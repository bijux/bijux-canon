#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Run the installed CPU exact/ANN hybrid workflow and development gate."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import shutil
import sys
from typing import Any, cast

from offline_lexical_workflow import (
    InstalledRuntime,
    WorkflowFailure,
    _inspect_run,
    _installed_environment,
    _job_result,
    _mapping,
    _read_artifact,
    _require,
    _string,
    _terminal_identity,
)

_EXACT_PROFILE = "local-hybrid-exact"
_ANN_PROFILE = "local-hybrid-ann"
_MODEL_PROFILE = "local-minilm-384"
_QUESTION = (
    "Which petrous-bone region produced the highest endogenous ancient-DNA yield?"
)
_QUALITY_FLOORS = {
    "recall-at-5": 0.90,
    "mrr-at-10": 0.85,
    "ndcg-at-10": 0.85,
}


def _arguments() -> argparse.Namespace:
    example = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-command", default="bijux-canon-runtime")
    parser.add_argument("--index-command", default="bijux-canon-index")
    parser.add_argument("--model-directory", type=Path, required=True)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--corpus-directory", type=Path, default=example / "corpus" / "sources"
    )
    parser.add_argument(
        "--cases", type=Path, default=example / "truth" / "evaluation-cases.jsonl"
    )
    parser.add_argument("--qrels", type=Path, default=example / "truth" / "qrels.jsonl")
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--question", default=_QUESTION)
    return parser.parse_args()


def _command(value: str, label: str) -> Path:
    selected = Path(shutil.which(value) or value).resolve()
    _require(selected.is_file(), f"{label} command not found: {value}")
    return selected


def _channels(evidence_set: dict[str, Any]) -> set[str]:
    raw_hits = evidence_set.get("hits")
    _require(isinstance(raw_hits, list) and raw_hits, "search returned no hits")
    hits = cast(list[object], raw_hits)
    channels: set[str] = set()
    for raw_hit in hits:
        hit = _mapping(raw_hit, "search hit is invalid")
        raw_channels = hit.get("channels")
        _require(isinstance(raw_channels, list), "search hit omitted channels")
        for raw_channel in cast(list[object], raw_channels):
            channel = _mapping(raw_channel, "search channel is invalid")
            channels.add(_string(channel.get("channel"), "channel name is invalid"))
    return channels


def _search(
    runtime: InstalledRuntime,
    *,
    evidence_name: str,
    question: str,
    index_id: str,
    profile: str,
    request_id: str,
) -> tuple[dict[str, Any], dict[str, Any], dict[str, Any]]:
    _, result = _job_result(
        runtime,
        evidence_name,
        "search",
        question,
        "--index-id",
        index_id,
        "--top-k",
        "1",
        "--request-id",
        request_id,
        "--idempotency-key",
        request_id,
        "--profile",
        profile,
    )
    inspection = _inspect_run(runtime, f"{evidence_name}-inspection", result)
    raw_hits = inspection.get("hits")
    _require(isinstance(raw_hits, list) and raw_hits, "inspection omitted search hits")
    hit_reference = _mapping(
        cast(list[object], raw_hits)[0], "hit reference is invalid"
    )
    artifact_id = _string(
        hit_reference.get("source_artifact_id"), "hit artifact identity is missing"
    )
    evidence_set = _mapping(
        json.loads(_read_artifact(runtime, artifact_id, f"{evidence_name}-evidence")),
        "search evidence set is invalid",
    )
    return result, inspection, evidence_set


def _assert_dense_execution(
    evidence_set: dict[str, Any], *, requested_profile: str, dense_channel: str
) -> None:
    _require(
        evidence_set.get("requested_retrieval_mode") == requested_profile,
        "requested retrieval mode was not retained",
    )
    _require(
        evidence_set.get("retrieval_mode") == requested_profile,
        "retrieval mode did not execute as requested",
    )
    retrieval = _mapping(evidence_set.get("retrieval"), "retrieval evidence is missing")
    dense = _mapping(retrieval.get("dense"), "dense execution evidence is missing")
    decision = _mapping(dense.get("decision"), "dense VEX decision is missing")
    _require(dense.get("outcome") == "success", "dense execution did not succeed")
    _require(decision.get("status") == "admitted", "dense VEX was not admitted")
    _require(retrieval.get("fallback_action") == "none", "dense execution fell back")
    channels = _channels(evidence_set)
    _require("lexical" in channels, "hybrid result omitted lexical contribution")
    _require(dense_channel in channels, f"hybrid result omitted {dense_channel}")


def _metric_values(evaluation: dict[str, Any]) -> dict[str, float]:
    macro = _mapping(evaluation.get("macro"), "evaluation omitted macro metrics")
    raw_metrics = macro.get("metrics")
    _require(isinstance(raw_metrics, list), "evaluation metrics are invalid")
    values: dict[str, float] = {}
    for raw_metric in cast(list[object], raw_metrics):
        metric = _mapping(raw_metric, "evaluation metric is invalid")
        metric_id = _string(metric.get("metric_id"), "metric identity is invalid")
        value = metric.get("value")
        _require(
            isinstance(value, int | float) and not isinstance(value, bool),
            f"metric value is invalid: {metric_id}",
        )
        values[metric_id] = float(cast(int | float, value))
    _require(values.keys() == _QUALITY_FLOORS.keys(), "evaluation metric set drifted")
    return values


def main() -> int:
    """Execute real model validation, indexing, retrieval, restart, and scoring."""

    args = _arguments()
    runtime_command = _command(args.runtime_command, "Runtime")
    index_command = _command(args.index_command, "Index")
    workspace = args.workspace.resolve()
    model_directory = args.model_directory.resolve()
    sources = args.corpus_directory.resolve()
    cases = args.cases.resolve()
    qrels = args.qrels.resolve()
    evidence = args.evidence_directory.resolve()
    for path, label in (
        (model_directory, "model directory"),
        (sources, "corpus directory"),
    ):
        _require(path.is_dir(), f"{label} not found: {path}")
    for path, label in ((cases, "cases"), (qrels, "qrels")):
        _require(path.is_file(), f"{label} not found: {path}")
    _require(not workspace.exists(), f"workspace must not exist: {workspace}")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    _require(
        not any(evidence.iterdir()), f"evidence directory must be empty: {evidence}"
    )

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.update(
        {
            "ALL_PROXY": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
            "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH": str(model_directory),
        }
    )
    relative_environment = dict(environment)
    relative_environment["BIJUX_CANON_RUNTIME_WORKING_ROOT"] = workspace.name
    runtime = InstalledRuntime(
        runtime_command,
        cwd=workspace.parent,
        evidence_directory=evidence,
        environment=relative_environment,
    )
    index = InstalledRuntime(
        index_command,
        cwd=workspace.parent,
        evidence_directory=evidence,
        environment=relative_environment,
    )
    installed = _installed_environment(runtime_command, evidence)

    validation = index.invoke(
        "model-validation",
        "model",
        "validate",
        "--profile",
        _MODEL_PROFILE,
        "--model-root",
        str(model_directory),
    )
    _require(validation.get("validation_result") == "passed", "model is invalid")
    _require(validation.get("offline_reuse") is True, "model is not reusable offline")
    _require(validation.get("dimension") == 384, "model dimension is not 384")
    model_lock_id = _string(
        validation.get("model_lock_artifact_id"), "model lock identity is missing"
    )

    initialization = runtime.invoke(
        "workspace-initialization",
        "init",
        "--workspace",
        workspace.name,
        "--model",
        str(model_directory),
        "--json",
    )
    _require(initialization.get("status") == "initialized", "initialization failed")
    _require(
        initialization.get("model_lock_artifact_id") == model_lock_id,
        "workspace model identity drifted",
    )
    discovery = runtime.invoke(
        "source-discovery",
        "v2",
        "discover",
        str(sources),
        "--root-name",
        "ancient-dna-research",
    )
    _require(discovery.get("complete") is True, "source discovery was incomplete")
    _require(len(discovery.get("sources", [])) == 8, "source discovery omitted files")
    for profile in (_EXACT_PROFILE, _ANN_PROFILE):
        readiness = runtime.invoke(
            f"{profile}-readiness",
            "v2",
            "ready",
            "--operation",
            "index",
            "--profile",
            profile,
        )
        _require(readiness.get("ready") is True, f"{profile} is not ready")

    corpus_job, corpus_result = _job_result(
        runtime,
        "corpus",
        "ingest",
        str(sources),
        "--request-id",
        "request-ancient-dna-cpu-ingest",
        "--idempotency-key",
        "ancient-dna-cpu-ingest",
        "--profile",
        _EXACT_PROFILE,
    )
    corpus_id = _terminal_identity(corpus_result, "corpus")
    corpus_inspection = runtime.invoke(
        "corpus-inspection", "v2", "corpus-inspect", corpus_id
    )
    _require(corpus_inspection.get("document_count") == 8, "corpus omitted documents")
    _require(corpus_inspection.get("chunk_count") == 493, "reviewed chunks drifted")
    _require(corpus_inspection.get("rejection_count") == 0, "corpus rejected sources")

    index_job, index_result = _job_result(
        runtime,
        "hybrid-index",
        "index",
        corpus_id,
        "--request-id",
        "request-ancient-dna-cpu-index",
        "--idempotency-key",
        "ancient-dna-cpu-index",
        "--profile",
        _EXACT_PROFILE,
    )
    index_id = _terminal_identity(index_result, "hybrid index")
    index_inspection = runtime.invoke(
        "hybrid-index-inspection", "v2", "index-inspect", index_id
    )
    integrity = _mapping(
        index_inspection.get("integrity"), "index integrity is missing"
    )
    _require(integrity.get("status") == "verified", "index integrity failed")
    _require(index_inspection.get("dimension") == 384, "index dimension drifted")
    _require(
        index_inspection.get("model_lock_artifact_id") == model_lock_id,
        "index model identity drifted",
    )
    raw_segments = index_inspection.get("segments")
    _require(isinstance(raw_segments, list), "index segments are missing")
    segments = cast(list[dict[str, Any]], raw_segments)
    _require(
        {(item.get("stage"), item.get("backend")) for item in segments}
        == {
            ("lexical", "sqlite-fts5"),
            ("dense_exact", "faiss-flat-ip"),
            ("dense_hnsw", "faiss-hnsw"),
        },
        "index did not persist all documented segments",
    )

    absolute_environment = dict(environment)
    absolute_environment["BIJUX_CANON_RUNTIME_WORKING_ROOT"] = str(workspace)
    runtime.environment = absolute_environment
    for profile in (_EXACT_PROFILE, _ANN_PROFILE):
        reopened = runtime.invoke(
            f"restarted-{profile}-readiness",
            "v2",
            "ready",
            "--operation",
            "retrieve",
            "--profile",
            profile,
        )
        _require(reopened.get("ready") is True, f"restart failed for {profile}")

    exact_result, _, exact_evidence = _search(
        runtime,
        evidence_name="exact-search",
        question=args.question,
        index_id=index_id,
        profile=_EXACT_PROFILE,
        request_id="request-ancient-dna-exact-search",
    )
    _assert_dense_execution(
        exact_evidence,
        requested_profile=_EXACT_PROFILE,
        dense_channel="dense-exact",
    )
    ann_result, _, ann_evidence = _search(
        runtime,
        evidence_name="ann-search",
        question=args.question,
        index_id=index_id,
        profile=_ANN_PROFILE,
        request_id="request-ancient-dna-ann-search",
    )
    _assert_dense_execution(
        ann_evidence,
        requested_profile=_ANN_PROFILE,
        dense_channel="dense-ann",
    )

    _, _, exact_repeat_evidence = _search(
        runtime,
        evidence_name="exact-search-repeat",
        question=args.question,
        index_id=index_id,
        profile=_EXACT_PROFILE,
        request_id="request-ancient-dna-exact-search-repeat",
    )
    _, _, ann_repeat_evidence = _search(
        runtime,
        evidence_name="ann-search-repeat",
        question=args.question,
        index_id=index_id,
        profile=_ANN_PROFILE,
        request_id="request-ancient-dna-ann-search-repeat",
    )
    _require(
        [item["chunk_id"] for item in exact_repeat_evidence["hits"]]
        == [item["chunk_id"] for item in exact_evidence["hits"]]
        and _channels(exact_repeat_evidence) == _channels(exact_evidence),
        "exact restart ranking is not deterministic",
    )
    _require(
        [item["chunk_id"] for item in ann_repeat_evidence["hits"]]
        == [item["chunk_id"] for item in ann_evidence["hits"]]
        and _channels(ann_repeat_evidence) == _channels(ann_evidence),
        "ANN restart ranking is not deterministic",
    )

    evaluation = runtime.invoke(
        "development-retrieval-evaluation",
        "v2",
        "evaluate-retrieval",
        "--cases",
        str(cases),
        "--qrels",
        str(qrels),
        "--index-id",
        index_id,
        "--split",
        "development",
        "--mode",
        _EXACT_PROFILE,
    )
    metrics = _metric_values(evaluation)
    for metric_id, floor in _QUALITY_FLOORS.items():
        _require(metrics[metric_id] >= floor, f"{metric_id} is below {floor}")
    _require(evaluation.get("query_count") == 12, "evaluation query count drifted")
    _require(evaluation.get("qrel_count") == 29, "evaluation qrel count drifted")
    observations = evaluation.get("observations")
    _require(isinstance(observations, list), "evaluation observations are missing")
    observed_queries = cast(list[object], observations)
    _require(
        len(observed_queries) == 12
        and all(
            isinstance(item, dict) and item.get("status") == "success"
            for item in observed_queries
        ),
        "evaluation contains incomplete queries",
    )
    micro = _mapping(evaluation.get("micro"), "evaluation omitted micro metrics")
    _require(micro.get("failed_queries") == 0, "evaluation contains failures")
    _require(micro.get("refused_queries") == 0, "evaluation contains refusals")

    exact_run_id = _string(
        exact_result.get("run_id"), "exact search run identity is missing"
    )
    ann_run_id = _string(ann_result.get("run_id"), "ANN search run identity is missing")
    _require(exact_run_id == ann_run_id, "exact and ANN used different run identities")

    exact_hits = cast(list[dict[str, Any]], exact_evidence["hits"])
    ann_hits = cast(list[dict[str, Any]], ann_evidence["hits"])
    summary = {
        "corpus": {
            "artifact_id": corpus_id,
            "chunk_count": corpus_inspection["chunk_count"],
            "document_count": corpus_inspection["document_count"],
            "rejection_count": corpus_inspection["rejection_count"],
        },
        "evaluation": {
            "evidence_sha256": evaluation["evidence_sha256"],
            "metrics": metrics,
            "qrel_count": evaluation["qrel_count"],
            "query_count": evaluation["query_count"],
            "quality_floors": _QUALITY_FLOORS,
        },
        "index": {
            "artifact_id": index_id,
            "configuration_id": index_inspection["build"]["configuration_id"],
            "dimension": index_inspection["dimension"],
            "generation_id": index_inspection["generation_id"],
            "integrity": index_inspection["integrity"]["status"],
            "segments": segments,
        },
        "installed_environment": installed,
        "jobs": {
            "corpus": {
                "attempt_id": corpus_result["attempt_id"],
                "job_id": corpus_job["job_id"],
                "run_id": corpus_result["run_id"],
            },
            "index": {
                "attempt_id": index_result["attempt_id"],
                "job_id": index_job["job_id"],
                "run_id": index_result["run_id"],
            },
        },
        "model": {
            "artifact_set_digest": validation["artifact_set_digest"],
            "dimension": validation["dimension"],
            "license_expression": validation["license_expression"],
            "model_lock_artifact_id": model_lock_id,
            "profile_id": validation["profile_id"],
            "revision": validation["revision"],
            "source": validation["source"],
            "validation_result": validation["validation_result"],
        },
        "network_isolation": os.environ.get(
            "BIJUX_CANON_NETWORK_ISOLATION", "proxy-denied"
        ),
        "question": args.question,
        "result": "passed",
        "run_id": exact_run_id,
        "schema_version": "bijux.canon.example.cpu_hybrid_workflow.v1",
        "searches": {
            "ann": {
                "attempt_id": ann_result["attempt_id"],
                "channels": sorted(_channels(ann_evidence)),
                "chunk_id": ann_hits[0]["chunk_id"],
                "deterministic_repeat": True,
                "run_id": ann_result["run_id"],
            },
            "exact": {
                "attempt_id": exact_result["attempt_id"],
                "channels": sorted(_channels(exact_evidence)),
                "chunk_id": exact_hits[0]["chunk_id"],
                "deterministic_repeat": True,
                "run_id": exact_result["run_id"],
            },
        },
        "workspace": {
            "absolute_reopen": str(workspace),
            "initial_spelling": workspace.name,
            "restart_ready_profiles": [_EXACT_PROFILE, _ANN_PROFILE],
        },
    }
    _require(
        summary["searches"]["exact"]["chunk_id"]
        == summary["searches"]["ann"]["chunk_id"],
        "exact and ANN did not return graded-equivalent top evidence",
    )
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, WorkflowFailure, json.JSONDecodeError) as error:
        print(f"CPU hybrid workflow failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
