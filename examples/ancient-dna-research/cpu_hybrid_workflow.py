#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Run the installed CPU exact/ANN hybrid workflow and development gate."""

from __future__ import annotations

import argparse
import hashlib
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
_RAG_TOP_K = 10
_RESEARCH_QUESTION_ID = "adna-multihop-contamination-strategy"
_RESEARCH_TOP_K = 10
_RESEARCH_BUDGET = {
    "max_artifact_bytes": 10_000_000,
    "max_provider_tokens": 100_000,
    "max_steps": 20,
    "operation_timeout_seconds": 120,
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


def _development_cases(path: Path) -> tuple[dict[str, Any], ...]:
    rows = tuple(
        _mapping(json.loads(line), "evaluation case is invalid")
        for line in path.read_text(encoding="utf-8").splitlines()
        if line.strip()
    )
    development = tuple(
        sorted(
            (item for item in rows if item.get("split") == "development"),
            key=lambda item: _string(item.get("case_id"), "case identity is invalid"),
        )
    )
    _require(len(development) == 12, "development case population drifted")
    _require(
        all(
            item.get("system_output_may_define_truth") is False for item in development
        ),
        "development truth permits system output to define labels",
    )
    return development


def _validate_system_output(
    output: dict[str, Any],
    *,
    case: dict[str, Any],
    result: dict[str, Any],
    source_hashes: set[str],
) -> dict[str, Any]:
    case_id = _string(case.get("case_id"), "case identity is missing")
    truth = _mapping(case.get("truth"), f"{case_id} truth is missing")
    expected = _string(
        truth.get("expected_disposition"), f"{case_id} disposition is missing"
    )
    observed = _string(
        output.get("disposition"), f"{case_id} output disposition is missing"
    )
    claims_value = output.get("claims")
    citations_value = output.get("citations")
    _require(isinstance(claims_value, list), f"{case_id} claims are invalid")
    _require(isinstance(citations_value, list), f"{case_id} citations are invalid")
    claims = tuple(
        _mapping(item, f"{case_id} claim is invalid")
        for item in cast(list[object], claims_value)
    )
    citations = tuple(
        _mapping(item, f"{case_id} citation is invalid")
        for item in cast(list[object], citations_value)
    )
    _require(
        output.get("schema_version") == "bijux.canon.evaluation.system-output.v1"
        and output.get("system_output_may_define_truth") is False,
        f"{case_id} output crossed the truth boundary",
    )
    _require(output.get("case_id") == case_id, f"{case_id} output identity drifted")
    _require(
        output.get("runtime_run_id") == result.get("run_id")
        and output.get("runtime_attempt_id") == result.get("attempt_id"),
        f"{case_id} output is not bound to its persisted attempt",
    )
    trace_identity = _string(
        output.get("trace_identity_sha256"), f"{case_id} trace identity is missing"
    )
    _require(
        len(trace_identity) == 64
        and all(character in "0123456789abcdef" for character in trace_identity),
        f"{case_id} trace identity is invalid",
    )
    citation_ids = {
        _string(item.get("citation_id"), f"{case_id} citation identity is missing")
        for item in citations
    }
    _require(len(citation_ids) == len(citations), f"{case_id} citations are duplicated")
    for citation in citations:
        exact_text = _string(
            citation.get("exact_text"), f"{case_id} citation text is missing"
        )
        exact_sha256 = _string(
            citation.get("exact_text_sha256"),
            f"{case_id} citation text hash is missing",
        )
        source_sha256 = _string(
            citation.get("source_sha256"),
            f"{case_id} citation source hash is missing",
        )
        _require(
            hashlib.sha256(exact_text.encode("utf-8")).hexdigest() == exact_sha256,
            f"{case_id} citation text hash drifted",
        )
        _require(
            source_sha256 in source_hashes,
            f"{case_id} citation does not resolve to a locked source",
        )
        _require(
            isinstance(citation.get("chunk_id"), str)
            and cast(str, citation["chunk_id"]).startswith("sha256:"),
            f"{case_id} citation chunk identity is missing",
        )
        character_start = citation.get("character_start")
        character_end = citation.get("character_end")
        _require(
            isinstance(character_start, int)
            and not isinstance(character_start, bool)
            and isinstance(character_end, int)
            and not isinstance(character_end, bool)
            and character_end - character_start == len(exact_text),
            f"{case_id} citation bounds drifted",
        )
    referenced_citation_ids: set[str] = set()
    for claim in claims:
        _string(claim.get("statement"), f"{case_id} claim statement is missing")
        raw_claim_citations = claim.get("citation_ids")
        _require(
            isinstance(raw_claim_citations, list) and raw_claim_citations,
            f"{case_id} emitted an ungrounded material claim",
        )
        claim_citations = set(cast(list[str], raw_claim_citations))
        referenced_citation_ids.update(claim_citations)
        _require(
            claim_citations.issubset(citation_ids),
            f"{case_id} claim references an unresolved citation",
        )
    _require(
        referenced_citation_ids == citation_ids,
        f"{case_id} emitted an unreferenced citation",
    )
    allowed_dispositions = {
        "answer": {"answered"},
        "qualified-answer": {"answered", "partially_abstained"},
        "clarification-required": {"abstained"},
        "abstain": {"abstained"},
    }
    _require(
        observed in allowed_dispositions.get(expected, set()),
        f"{case_id} did not preserve its reviewed disposition",
    )
    if bool(truth.get("abstention_expected")):
        _require(
            observed == "abstained"
            and not output.get("answer")
            and not claims
            and not citations
            and isinstance(output.get("abstention_reason"), str),
            f"{case_id} did not preserve required abstention",
        )
    else:
        _require(
            observed in {"answered", "partially_abstained"} and claims and citations,
            f"{case_id} did not produce a grounded answer",
        )
        if expected == "qualified-answer":
            _require(
                any(item.get("disposition") == "qualified" for item in claims),
                f"{case_id} omitted reviewed qualification behavior",
            )
    return {
        "attempt_id": output["runtime_attempt_id"],
        "case_id": case_id,
        "citation_count": len(citations),
        "claim_count": len(claims),
        "disposition_match": True,
        "expected_disposition": expected,
        "verified_direct_support_claims": len(claims),
        "observed_disposition": observed,
        "output_id": output["output_id"],
        "run_id": output["runtime_run_id"],
        "trace_identity_sha256": trace_identity,
    }


def _evaluate_grounded_answers(
    runtime: InstalledRuntime,
    *,
    cases_path: Path,
    corpus_id: str,
    index_id: str,
    sources: Path,
    evidence: Path,
) -> dict[str, Any]:
    cases = _development_cases(cases_path)
    source_hashes = {
        hashlib.sha256(path.read_bytes()).hexdigest()
        for path in sorted(sources.glob("*.xml"))
    }
    _require(len(source_hashes) == 8, "locked source digest population drifted")
    outputs: list[dict[str, Any]] = []
    observations: list[dict[str, Any]] = []
    for case in cases:
        case_id = _string(case.get("case_id"), "case identity is invalid")
        question = _string(case.get("question"), f"{case_id} question is invalid")
        _, result = _job_result(
            runtime,
            f"rag-{case_id}",
            "ask",
            question,
            "--corpus-id",
            corpus_id,
            "--index-id",
            index_id,
            "--top-k",
            str(_RAG_TOP_K),
            "--request-id",
            f"request-{case_id}",
            "--idempotency-key",
            f"rag-{case_id}",
            "--profile",
            _EXACT_PROFILE,
        )
        output = runtime.invoke(
            f"rag-{case_id}-system-output",
            "v2",
            "evaluate-answer",
            _string(result.get("run_id"), f"{case_id} run identity is missing"),
            "--attempt-id",
            _string(result.get("attempt_id"), f"{case_id} attempt identity is missing"),
            "--case-id",
            case_id,
            "--question",
            question,
        )
        outputs.append(output)
        observations.append(
            _validate_system_output(
                output,
                case=case,
                result=result,
                source_hashes=source_hashes,
            )
        )
    (evidence / "rag-system-outputs.jsonl").write_text(
        "".join(json.dumps(item, sort_keys=True) + "\n" for item in outputs),
        encoding="utf-8",
    )
    citation_count = sum(item["citation_count"] for item in observations)
    claim_count = sum(item["claim_count"] for item in observations)
    # The installed evaluator rejects any exposed claim whose persisted grounding
    # admission is not bound to a direct-support verification verdict.
    verified_direct_support_claims = sum(
        item["verified_direct_support_claims"] for item in observations
    )
    return {
        "case_count": len(observations),
        "citation_count": citation_count,
        "citation_resolution_ratio": 1.0,
        "claim_count": claim_count,
        "development_disposition_matches": sum(
            bool(item["disposition_match"]) for item in observations
        ),
        "grounding_admission_support_ratio": (
            verified_direct_support_claims / claim_count if claim_count else 1.0
        ),
        "verified_direct_support_claims": verified_direct_support_claims,
        "observations": observations,
        "semantic_equivalence_review_status": "pending-independent-review",
        "structurally_ungrounded_material_claims": 0,
        "system_output_may_define_truth": False,
        "top_k": _RAG_TOP_K,
        "unsupported_material_claims": claim_count - verified_direct_support_claims,
    }


def _evaluate_bounded_research(
    runtime: InstalledRuntime,
    *,
    cases_path: Path,
    corpus_id: str,
    index_id: str,
) -> dict[str, Any]:
    cases = tuple(
        item
        for item in _development_cases(cases_path)
        if item.get("question_id") == _RESEARCH_QUESTION_ID
    )
    _require(len(cases) == 1, "bounded research case selection drifted")
    case = cases[0]
    case_id = _string(case.get("case_id"), "research case identity is missing")
    question = _string(case.get("question"), "research question is missing")
    _require(
        case.get("system_output_may_define_truth") is False,
        "research case permits system output to define truth",
    )
    job, result = _job_result(
        runtime,
        "bounded-research",
        "research",
        question,
        "--corpus-id",
        corpus_id,
        "--index-id",
        index_id,
        "--top-k",
        str(_RESEARCH_TOP_K),
        "--request-id",
        f"request-{case_id}-research",
        "--idempotency-key",
        f"research-{case_id}",
        "--profile",
        _EXACT_PROFILE,
        "--operation-timeout-seconds",
        str(_RESEARCH_BUDGET["operation_timeout_seconds"]),
        "--max-artifact-bytes",
        str(_RESEARCH_BUDGET["max_artifact_bytes"]),
        "--max-steps",
        str(_RESEARCH_BUDGET["max_steps"]),
        "--max-provider-tokens",
        str(_RESEARCH_BUDGET["max_provider_tokens"]),
    )
    _require(result.get("status") == "completed", "research run did not complete")
    publication_id = _terminal_identity(result, "bounded research")
    publication = _mapping(
        json.loads(_read_artifact(runtime, publication_id, "bounded-research-receipt")),
        "research publication receipt is invalid",
    )
    _require(
        publication.get("schema_version")
        == "bijux.canon.runtime.publication_receipt.v1"
        and publication.get("status") == "published-local",
        "research publication receipt is invalid",
    )
    trace_id = _string(
        publication.get("subject_artifact_id"), "research trace identity is missing"
    )
    trace = _mapping(
        json.loads(_read_artifact(runtime, trace_id, "bounded-research-trace")),
        "research trace is invalid",
    )
    _require(
        trace.get("schema_version") == "bijux.canon.agent.research_trace.v1",
        "research trace schema drifted",
    )

    raw_plans = trace.get("targeted_search_plans")
    _require(isinstance(raw_plans, list), "research search plans are invalid")
    plans = tuple(
        _mapping(item, "research search plan is invalid")
        for item in cast(list[object], raw_plans)
    )
    _require(len(plans) >= 2, "research did not pursue distinct evidence needs")
    attempts = tuple(
        _mapping(item.get("attempt"), "research search attempt is invalid")
        for item in plans
    )
    query_identities = tuple(
        _string(
            item.get("query_equivalence_sha256"),
            "research query identity is missing",
        )
        for item in attempts
    )
    requirement_identities = tuple(
        _string(
            item.get("requirement_artifact_id"),
            "research requirement identity is missing",
        )
        for item in attempts
    )
    _require(
        len(query_identities) == len(set(query_identities))
        and len(requirement_identities) == len(set(requirement_identities)),
        "research repeated an equivalent query or evidence need",
    )
    raw_observations = trace.get("targeted_search_observations")
    raw_runs = trace.get("counterevidence_runs")
    raw_retrieval_ids = trace.get("counterevidence_retrieval_artifact_ids")
    _require(
        isinstance(raw_observations, list)
        and isinstance(raw_runs, list)
        and isinstance(raw_retrieval_ids, list)
        and len(raw_observations) == len(plans)
        and len(raw_runs) == len(plans)
        and len(raw_retrieval_ids) == len(plans),
        "research search evidence is incomplete",
    )

    raw_classifications = trace.get("candidate_classifications")
    _require(
        isinstance(raw_classifications, list) and raw_classifications,
        "research omitted candidate classifications",
    )
    classifications = tuple(
        _mapping(item, "research candidate classification is invalid")
        for item in cast(list[object], raw_classifications)
    )
    relations = tuple(
        _string(item.get("relation"), "research candidate relation is missing")
        for item in classifications
    )
    _require(
        all(
            relation
            in {
                "supporting",
                "opposing",
                "limiting",
                "irrelevant",
                "ambiguous",
                "unclassified",
            }
            for relation in relations
        )
        and any(item.get("material") is True for item in classifications),
        "research candidate classifications are not admissible",
    )

    revision = _mapping(trace.get("answer_revision"), "research revision is missing")
    before_answer = _string(
        revision.get("before_answer"), "research initial answer is missing"
    )
    after_answer = _string(
        revision.get("after_answer"), "research revised answer is missing"
    )
    _require(
        revision.get("outcome") == "revised"
        and before_answer
        and after_answer
        and before_answer != after_answer
        and trace.get("answer") == after_answer,
        "research did not retain and warrant its answer revision",
    )
    revised_answer = _mapping(
        revision.get("revised_answer"), "research revised answer record is missing"
    )
    presentation = _mapping(
        revised_answer.get("citation_presentation"),
        "research citation presentation is missing",
    )
    raw_citations = presentation.get("entries")
    admission = _mapping(
        revised_answer.get("admission"), "research answer admission is missing"
    )
    raw_admitted_claims = admission.get("admitted_claim_artifact_ids")
    _require(
        isinstance(raw_citations, list)
        and raw_citations
        and isinstance(raw_admitted_claims, list)
        and raw_admitted_claims,
        "research final conclusion is not cited and admitted",
    )
    citations = tuple(
        _mapping(item, "research citation is invalid")
        for item in cast(list[object], raw_citations)
    )
    cited_claim_ids = {
        claim_id
        for citation in citations
        for claim_id in cast(list[str], citation.get("claim_artifact_ids", []))
    }
    admitted_claim_ids = set(cast(list[str], raw_admitted_claims))
    _require(
        admitted_claim_ids.issubset(cited_claim_ids),
        "research final conclusion contains an uncited admitted claim",
    )

    termination = _mapping(
        trace.get("termination"), "research termination evidence is missing"
    )
    raw_reasons = termination.get("reasons")
    outcome = _mapping(
        trace.get("research_outcome"), "research terminal outcome is missing"
    )
    _require(
        termination.get("stop") is True
        and isinstance(raw_reasons, list)
        and raw_reasons
        and outcome.get("kind") in {"complete", "incomplete_budget"}
        and trace.get("tool_failure_artifact_ids") == [],
        "research did not stop with an inspectable successful reason",
    )
    budget_policy = _mapping(
        trace.get("budget_policy"), "research budget policy is missing"
    )
    global_limits = _mapping(
        budget_policy.get("global_limits"), "research global limits are missing"
    )
    budget_usage = _mapping(
        trace.get("budget_usage"), "research budget usage is missing"
    )
    for dimension in (
        "artifact_bytes",
        "candidates",
        "documents",
        "elapsed_ms",
        "evidence_items",
        "iterations",
        "retrievals",
        "tokens",
        "tool_calls",
    ):
        limit = global_limits.get(dimension)
        used = budget_usage.get(dimension)
        _require(
            isinstance(limit, int)
            and not isinstance(limit, bool)
            and isinstance(used, int)
            and not isinstance(used, bool)
            and 0 <= used <= limit,
            f"research {dimension} budget is invalid",
        )

    relation_counts = {
        relation: relations.count(relation) for relation in sorted(set(relations))
    }
    return {
        "answer_changed": True,
        "attempt_id": result["attempt_id"],
        "budget_limits": global_limits,
        "budget_usage": budget_usage,
        "case_id": case_id,
        "classification_count": len(classifications),
        "classification_relations": relation_counts,
        "convergence_outcome": outcome["convergence_outcome"],
        "distinct_evidence_needs": len(requirement_identities),
        "distinct_searches": len(query_identities),
        "final_admitted_claim_count": len(admitted_claim_ids),
        "final_citation_count": len(citations),
        "initial_answer_retained": True,
        "job_id": job["job_id"],
        "question_id": _RESEARCH_QUESTION_ID,
        "revision_outcome": revision["outcome"],
        "run_id": result["run_id"],
        "stop_reasons": raw_reasons,
        "system_output_may_define_truth": False,
        "terminal_outcome": outcome["kind"],
        "tool_failure_count": 0,
        "trace_artifact_id": trace_id,
    }


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

    rag = _evaluate_grounded_answers(
        runtime,
        cases_path=cases,
        corpus_id=corpus_id,
        index_id=index_id,
        sources=sources,
        evidence=evidence,
    )
    research = _evaluate_bounded_research(
        runtime,
        cases_path=cases,
        corpus_id=corpus_id,
        index_id=index_id,
    )

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
        "rag": rag,
        "research": research,
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
