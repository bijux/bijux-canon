#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Run and verify the installed, model-free ancient-DNA product workflow."""

from __future__ import annotations

import argparse
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Any, cast
import xml.etree.ElementTree as ET

_PROFILE = "offline-lexical"
_QUESTION = "What contamination controls are recommended for ancient DNA?"
_PAGE_BYTES = 65_536
_PATH_PART = re.compile(r"^([^\[]+)\[(\d+)\]$")


class WorkflowFailure(RuntimeError):
    """Raised when installed behavior does not satisfy the example contract."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise WorkflowFailure(message)


def _mapping(value: object, message: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise WorkflowFailure(message)
    return cast(dict[str, Any], value)


def _string(value: object, message: str) -> str:
    if not isinstance(value, str):
        raise WorkflowFailure(message)
    return value


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _resolve_jats_element(source: Path, element_path: str) -> ET.Element:
    root = ET.parse(source).getroot()  # noqa: S314 - reviewed local example bytes
    parts = [part for part in element_path.split("/") if part]
    _require(parts, f"empty JATS element path for {source.name}")
    current = root
    root_match = _PATH_PART.fullmatch(parts[0])
    _require(root_match is not None, f"invalid JATS path component: {parts[0]}")
    assert root_match is not None
    _require(
        _local_name(root.tag) == root_match.group(1) and root_match.group(2) == "1",
        f"JATS path root does not identify {source.name}",
    )
    for part in parts[1:]:
        match = _PATH_PART.fullmatch(part)
        _require(match is not None, f"invalid JATS path component: {part}")
        assert match is not None
        children = [
            child for child in current if _local_name(child.tag) == match.group(1)
        ]
        ordinal = int(match.group(2))
        _require(
            1 <= ordinal <= len(children),
            f"JATS path component does not resolve: {part}",
        )
        current = children[ordinal - 1]
    return current


def _normalized_text(value: str) -> str:
    return " ".join(value.split())


class InstalledRuntime:
    """Capture every installed CLI exchange as durable JSON evidence."""

    def __init__(
        self,
        command: Path,
        *,
        cwd: Path,
        evidence_directory: Path,
        environment: dict[str, str],
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.evidence_directory = evidence_directory
        self.environment = environment

    def invoke(
        self,
        evidence_name: str,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        completed = subprocess.run(  # noqa: S603 - explicit operator-selected command
            [str(self.command), *arguments],
            cwd=self.cwd,
            env=environment or self.environment,
            capture_output=True,
            check=False,
            text=True,
        )
        record = {
            "arguments": list(arguments),
            "returncode": completed.returncode,
            "stderr": completed.stderr,
            "stdout": completed.stdout,
        }
        (self.evidence_directory / f"{evidence_name}.exchange.json").write_text(
            json.dumps(record, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        _require(
            completed.returncode == 0,
            f"{evidence_name} failed with exit {completed.returncode}: "
            f"{completed.stderr.strip()}",
        )
        try:
            value = json.loads(completed.stdout)
        except json.JSONDecodeError as error:
            raise WorkflowFailure(f"{evidence_name} did not return JSON") from error
        value = _mapping(value, f"{evidence_name} returned a non-object")
        (self.evidence_directory / f"{evidence_name}.json").write_text(
            json.dumps(value, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        return value


def _job_result(
    runtime: InstalledRuntime,
    evidence_name: str,
    *arguments: str,
) -> tuple[dict[str, Any], dict[str, Any]]:
    status = runtime.invoke(
        f"{evidence_name}-job",
        "v2",
        *arguments,
        "--wait",
        "--wait-timeout-seconds",
        "120",
    )
    _require(status.get("status") == "succeeded", f"{evidence_name} job failed")
    job_id = _string(status.get("job_id"), f"{evidence_name} omitted its job identity")
    result_envelope = runtime.invoke(f"{evidence_name}-result", "v2", "result", job_id)
    result = _mapping(
        result_envelope.get("result"), f"{evidence_name} omitted its result"
    )
    return status, result


def _terminal_identity(result: dict[str, Any], evidence_name: str) -> str:
    raw_identities = result.get("terminal_artifact_ids")
    _require(
        isinstance(raw_identities, list)
        and len(raw_identities) == 1
        and isinstance(raw_identities[0], str),
        f"{evidence_name} did not return one terminal artifact",
    )
    identities = cast(list[str], raw_identities)
    return identities[0]


def _inspect_run(
    runtime: InstalledRuntime, evidence_name: str, result: dict[str, Any]
) -> dict[str, Any]:
    run_id = _string(result.get("run_id"), f"{evidence_name} omitted its run identity")
    inspection = runtime.invoke(evidence_name, "v2", "inspect", run_id)
    page = inspection.get("page")
    _require(
        isinstance(page, dict) and page.get("limit") == 5,
        f"{evidence_name} did not use the bounded default inspection page",
    )
    counts = _mapping(
        inspection.get("collection_counts"),
        f"{evidence_name} omitted collection counts",
    )
    for collection, count in counts.items():
        values = inspection.get(collection)
        if isinstance(values, list):
            _require(
                len(values) <= 5 and isinstance(count, int) and count >= len(values),
                f"{evidence_name} returned an unbounded {collection} collection",
            )
    return inspection


def _read_artifact(
    runtime: InstalledRuntime, artifact_id: str, evidence_name: str
) -> bytes:
    payload = bytearray()
    offset = 0
    expected_total: int | None = None
    expected_sha256: str | None = None
    while True:
        page = runtime.invoke(
            f"{evidence_name}-page-{offset}",
            "v2",
            "artifact-payload",
            artifact_id,
            "--offset",
            str(offset),
            "--max-bytes",
            str(_PAGE_BYTES),
        )
        _require(
            page.get("artifact_id") == artifact_id, "artifact page identity drifted"
        )
        _require(page.get("offset") == offset, "artifact page offset drifted")
        total = page.get("total_bytes")
        digest = page.get("payload_sha256")
        _require(isinstance(total, int) and total > 0, "artifact total is invalid")
        _require(isinstance(digest, str), "artifact payload digest is missing")
        expected_total = total if expected_total is None else expected_total
        expected_sha256 = digest if expected_sha256 is None else expected_sha256
        _require(total == expected_total, "artifact total changed between pages")
        _require(digest == expected_sha256, "artifact digest changed between pages")
        encoded = _string(page.get("data_base64"), "artifact page data is missing")
        chunk = base64.b64decode(encoded, validate=True)
        _require(
            page.get("byte_length") == len(chunk), "artifact page length is invalid"
        )
        _require(len(chunk) <= _PAGE_BYTES, "artifact page exceeded its public bound")
        payload.extend(chunk)
        next_offset = page.get("next_offset")
        if next_offset is None:
            break
        _require(next_offset == offset + len(chunk), "artifact continuation is invalid")
        offset = next_offset
    _require(len(payload) == expected_total, "assembled artifact length is invalid")
    _require(
        hashlib.sha256(payload).hexdigest() == expected_sha256,
        "assembled artifact digest is invalid",
    )
    (runtime.evidence_directory / f"{evidence_name}.payload.json").write_bytes(payload)
    return bytes(payload)


def _verify_citations(
    claim_graph: dict[str, Any], inspection: dict[str, Any], sources: Path
) -> list[dict[str, Any]]:
    citation_set = _mapping(
        claim_graph.get("citations"), "claim graph omitted citations"
    )
    raw_links = citation_set.get("links")
    _require(isinstance(raw_links, list) and raw_links, "answer has no citation links")
    links = cast(list[object], raw_links)
    provenance = _mapping(inspection.get("provenance"), "answer provenance is missing")
    _require(
        provenance.get("status") == "verified",
        "answer provenance is not verified",
    )
    raw_provenance_citations = provenance.get("citations")
    _require(
        isinstance(raw_provenance_citations, list), "citation provenance is missing"
    )
    provenance_citations = cast(list[object], raw_provenance_citations)
    by_citation = {
        item["citation_id"]: item
        for item in provenance_citations
        if isinstance(item, dict) and isinstance(item.get("citation_id"), str)
    }
    verified: list[dict[str, Any]] = []
    for raw_link in links:
        link = _mapping(raw_link, "citation link is invalid")
        citation_id = link.get("artifact_id")
        lineage = _mapping(
            by_citation.get(citation_id), f"citation lineage is missing: {citation_id}"
        )
        source_name = _string(
            lineage.get("source_relative_path"), "citation source path is missing"
        )
        source = sources / source_name
        source_bytes = source.read_bytes()
        source_sha256 = hashlib.sha256(source_bytes).hexdigest()
        _require(
            source_sha256
            == link.get("source_content_sha256")
            == lineage.get("source_content_sha256"),
            f"citation source digest does not resolve: {source_name}",
        )
        _require(
            link.get("locator_scheme") == "jats-element-path", "unexpected locator"
        )
        raw_selectors = link.get("locator_selectors")
        _require(isinstance(raw_selectors, list), "citation selectors are missing")
        selectors = cast(list[tuple[str, str]], raw_selectors)
        selector_map = dict(selectors)
        element_path = _string(
            selector_map.get("element_path"), "JATS element path is missing"
        )
        element = _resolve_jats_element(source, element_path)
        exact_text = _string(link.get("exact_text"), "exact quote is missing")
        exact_sha256 = _string(
            link.get("exact_text_sha256"), "exact quote digest is missing"
        )
        _require(
            hashlib.sha256(exact_text.encode()).hexdigest() == exact_sha256,
            "exact citation quote digest is invalid",
        )
        _require(
            _normalized_text(exact_text)
            in _normalized_text(" ".join(element.itertext())),
            f"exact citation quote does not resolve: {source_name} {element_path}",
        )
        for required_identity in (
            "chunk_id",
            "corpus_snapshot_artifact_id",
            "document_id",
            "index_artifact_id",
            "parent_job_id",
            "run_id",
            "source_archive_artifact_id",
        ):
            _require(
                lineage.get(required_identity), f"citation omitted {required_identity}"
            )
        verified.append(
            {
                "chunk_id": lineage["chunk_id"],
                "citation_id": citation_id,
                "document_id": lineage["document_id"],
                "exact_text_sha256": exact_sha256,
                "locator": element_path,
                "resolved": True,
                "source_content_sha256": source_sha256,
                "source_relative_path": source_name,
            }
        )
    return verified


def _installed_environment(command: Path, evidence_directory: Path) -> dict[str, Any]:
    python = command.parent / "python"
    _require(
        python.is_file(), f"no environment Python beside installed command: {command}"
    )
    code = (
        "import importlib.metadata as m, json, sys; "
        "names=('bijux-canon-runtime','bijux-canon-ingest','bijux-canon-index',"
        "'bijux-canon-reason','bijux-canon-agent'); "
        "print(json.dumps({'distributions':{n:m.version(n) for n in names},"
        "'executable':sys.executable,'sys_path':sys.path},sort_keys=True))"
    )
    completed = subprocess.run(  # noqa: S603 - resolved sibling interpreter
        [str(python), "-I", "-c", code],
        capture_output=True,
        check=False,
        text=True,
    )
    _require(completed.returncode == 0, "installed environment metadata failed")
    value = _mapping(
        json.loads(completed.stdout), "installed environment returned a non-object"
    )
    (evidence_directory / "installed-environment.json").write_text(
        json.dumps(value, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    return value


def _arguments() -> argparse.Namespace:
    example = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-command", default="bijux-canon-runtime")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument(
        "--corpus-directory", type=Path, default=example / "corpus" / "sources"
    )
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--question", default=_QUESTION)
    return parser.parse_args()


def main() -> int:
    """Execute the complete public workflow and emit a compact verdict."""

    args = _arguments()
    command_value = shutil.which(args.runtime_command) or args.runtime_command
    command = Path(command_value).resolve()
    _require(command.is_file(), f"runtime command not found: {args.runtime_command}")
    workspace = args.workspace.resolve()
    sources = args.corpus_directory.resolve()
    evidence = args.evidence_directory.resolve()
    _require(sources.is_dir(), f"corpus directory not found: {sources}")
    _require(not workspace.exists(), f"workspace must not exist: {workspace}")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    _require(
        not any(evidence.iterdir()), f"evidence directory must be empty: {evidence}"
    )

    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH", None)
    environment.update(
        {
            "ALL_PROXY": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
        }
    )
    relative_environment = dict(environment)
    relative_environment["BIJUX_CANON_RUNTIME_WORKING_ROOT"] = workspace.name
    runtime = InstalledRuntime(
        command,
        cwd=workspace.parent,
        evidence_directory=evidence,
        environment=relative_environment,
    )
    installed = _installed_environment(command, evidence)

    initialization = runtime.invoke(
        "workspace-initialization",
        "init",
        "--workspace",
        workspace.name,
        "--json",
    )
    _require(
        initialization.get("status") == "initialized", "workspace was not initialized"
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
    _require(
        len(discovery.get("sources", [])) == 8, "source discovery did not admit 8 files"
    )
    _require(discovery.get("issues") == [], "source discovery reported issues")
    capabilities = runtime.invoke("capabilities", "v2", "capabilities")
    model = capabilities.get("model")
    _require(
        isinstance(model, dict) and model.get("status") == "unavailable",
        "model-free workspace unexpectedly resolved a model",
    )
    readiness = runtime.invoke(
        "lexical-readiness",
        "v2",
        "ready",
        "--operation",
        "index",
        "--profile",
        _PROFILE,
    )
    _require(readiness.get("ready") is True, "offline lexical profile is not ready")

    corpus_job, corpus_result = _job_result(
        runtime,
        "corpus",
        "ingest",
        str(sources),
        "--request-id",
        "request-ancient-dna-offline-ingest",
        "--idempotency-key",
        "ancient-dna-offline-ingest",
        "--profile",
        _PROFILE,
    )
    corpus_id = _terminal_identity(corpus_result, "corpus")
    corpus_inspection = runtime.invoke(
        "corpus-inspection", "v2", "corpus-inspect", corpus_id
    )
    _require(corpus_inspection.get("document_count") == 8, "corpus omitted documents")
    _require(corpus_inspection.get("chunk_count", 0) > 0, "corpus omitted chunks")
    _require(corpus_inspection.get("rejection_count") == 0, "corpus rejected sources")
    _require(
        corpus_inspection.get("parser_identities"), "corpus omitted parser identity"
    )

    index_job, index_result = _job_result(
        runtime,
        "lexical-index",
        "index",
        corpus_id,
        "--request-id",
        "request-ancient-dna-offline-index",
        "--idempotency-key",
        "ancient-dna-offline-index",
        "--profile",
        _PROFILE,
    )
    index_id = _terminal_identity(index_result, "lexical index")
    index_inspection = runtime.invoke(
        "lexical-index-inspection", "v2", "index-inspect", index_id
    )
    _require(index_inspection.get("backend") == "sqlite-fts5", "index is not lexical")
    _require(
        index_inspection.get("chunk_count") == corpus_inspection.get("chunk_count"),
        "corpus and index chunk counts differ",
    )

    search_job, search_result = _job_result(
        runtime,
        "evidence-search",
        "search",
        args.question,
        "--index-id",
        index_id,
        "--top-k",
        "5",
        "--request-id",
        "request-ancient-dna-offline-search",
        "--idempotency-key",
        "ancient-dna-offline-search",
        "--profile",
        _PROFILE,
    )
    search_inspection = _inspect_run(
        runtime, "evidence-search-inspection", search_result
    )
    _require(
        search_inspection["collection_counts"].get("hits", 0) > 0,
        "search returned no evidence",
    )

    answer_job, answer_result = _job_result(
        runtime,
        "grounded-answer",
        "ask",
        args.question,
        "--index-id",
        index_id,
        "--corpus-id",
        corpus_id,
        "--top-k",
        "5",
        "--request-id",
        "request-ancient-dna-offline-answer",
        "--idempotency-key",
        "ancient-dna-offline-answer",
        "--profile",
        _PROFILE,
    )
    answer_artifact_id = _terminal_identity(answer_result, "grounded answer")
    answer_inspection = _inspect_run(
        runtime, "grounded-answer-inspection", answer_result
    )
    _require(
        answer_inspection.get("status") == "completed", "answer run did not complete"
    )
    operations = [step.get("operation") for step in answer_inspection.get("steps", [])]
    _require(
        operations == ["retrieve", "reason", "verify", "persist", "publish"],
        f"unexpected answer operations: {operations}",
    )
    provenance = _mapping(
        answer_inspection.get("provenance"), "answer provenance is missing"
    )
    _require(
        provenance.get("model_lock_artifact_ids") == [], "lexical answer used a model"
    )
    raw_provenance_citations = provenance.get("citations")
    _require(
        isinstance(raw_provenance_citations, list) and raw_provenance_citations,
        "citations missing",
    )
    provenance_citations = cast(list[dict[str, Any]], raw_provenance_citations)
    claim_graph_id = _string(
        provenance_citations[0].get("claim_graph_artifact_id"),
        "claim graph identity is missing",
    )
    claim_graph_bytes = _read_artifact(
        runtime, claim_graph_id, "grounded-answer-claim-graph"
    )
    claim_graph = json.loads(claim_graph_bytes)
    _require(
        claim_graph.get("answer_disposition") == "admitted", "answer was not admitted"
    )
    citations = _verify_citations(claim_graph, answer_inspection, sources)

    absolute_environment = dict(environment)
    absolute_environment["BIJUX_CANON_RUNTIME_WORKING_ROOT"] = str(workspace)
    reopened = runtime.invoke(
        "restart-readiness",
        "v2",
        "ready",
        "--operation",
        "ask",
        "--profile",
        _PROFILE,
        environment=absolute_environment,
    )
    _require(reopened.get("ready") is True, "absolute-path restart is not ready")
    runtime.environment = absolute_environment
    reopened_inspection = _inspect_run(
        runtime, "restarted-answer-inspection", answer_result
    )
    _require(
        reopened_inspection.get("run_id") == answer_result.get("run_id"),
        "restart did not preserve the answer run",
    )

    replay_job, replay_result = _job_result(
        runtime,
        "answer-replay",
        "replay",
        str(answer_result["run_id"]),
        "--source-attempt-id",
        str(answer_result["attempt_id"]),
        "--network-policy",
        "disabled",
        "--request-id",
        "request-ancient-dna-offline-replay",
        "--idempotency-key",
        "ancient-dna-offline-replay",
    )
    _require(replay_result.get("accepted") is True, "replay was not accepted")
    _require(
        replay_result.get("exact_artifact_identities") is True,
        "replay changed artifact identities",
    )
    replay_attempt_id = _string(
        replay_result.get("replay_attempt_id"), "replay attempt identity is missing"
    )
    comparison = runtime.invoke(
        "answer-comparison",
        "v2",
        "compare",
        str(answer_result["run_id"]),
        str(replay_result["run_id"]),
        "--baseline-attempt-id",
        str(answer_result["attempt_id"]),
        "--candidate-attempt-id",
        replay_attempt_id,
        "--dimension",
        "outcome",
        "--dimension",
        "claims",
        "--dimension",
        "citations",
    )
    _require(
        comparison.get("equivalent") is True, "replay comparison is not equivalent"
    )
    _require(
        all(
            item.get("classification") == "equal" for item in comparison["differences"]
        ),
        "replay comparison contains a changed dimension",
    )

    summary = {
        "answer": claim_graph.get("answer"),
        "answer_artifact_id": answer_artifact_id,
        "answer_disposition": claim_graph.get("answer_disposition"),
        "claim_graph_artifact_id": claim_graph_id,
        "citations": citations,
        "corpus": {
            "artifact_id": corpus_id,
            "chunk_count": corpus_inspection["chunk_count"],
            "document_count": corpus_inspection["document_count"],
            "parser_identities": corpus_inspection["parser_identities"],
            "rejection_count": corpus_inspection["rejection_count"],
        },
        "index": {
            "artifact_id": index_id,
            "backend": index_inspection["backend"],
            "chunk_count": index_inspection["chunk_count"],
        },
        "installed_environment": installed,
        "jobs": {
            "answer": answer_job["job_id"],
            "corpus": corpus_job["job_id"],
            "index": index_job["job_id"],
            "replay": replay_job["job_id"],
            "search": search_job["job_id"],
        },
        "network_isolation": os.environ.get(
            "BIJUX_CANON_NETWORK_ISOLATION", "proxy-denied"
        ),
        "profile": _PROFILE,
        "question": args.question,
        "replay": {
            "attempt_id": replay_attempt_id,
            "comparison_sha256": comparison["comparison_sha256"],
            "equivalent": comparison["equivalent"],
            "exact_artifact_identities": replay_result["exact_artifact_identities"],
        },
        "result": "passed",
        "run": {
            "attempt_id": answer_result["attempt_id"],
            "bounded_inspection_limit": answer_inspection["page"]["limit"],
            "provenance_status": provenance["status"],
            "run_id": answer_result["run_id"],
        },
        "schema_version": "bijux.canon.example.offline_lexical_workflow.v1",
        "source_discovery": {
            "admitted_byte_count": discovery["admitted_byte_count"],
            "complete": discovery["complete"],
            "manifest_sha256": discovery["manifest_sha256"],
            "source_count": len(discovery["sources"]),
        },
        "workspace": {
            "absolute_reopen": str(workspace),
            "initial_spelling": workspace.name,
            "restart_ready": reopened["ready"],
        },
    }
    summary_path = evidence / "summary.json"
    summary_path.write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, WorkflowFailure, json.JSONDecodeError, ET.ParseError) as error:
        print(f"offline lexical workflow failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
