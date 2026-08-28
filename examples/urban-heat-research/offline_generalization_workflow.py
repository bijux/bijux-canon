#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Run the installed, model-free urban-heat generalization acceptance."""

from __future__ import annotations

import argparse
import base64
from collections.abc import Iterable
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any, cast

_PROFILE = "offline-lexical"
_PAGE_BYTES = 65_536
_RESEARCH_BUDGET = {
    "max_artifact_bytes": 10_000_000,
    "max_provider_tokens": 100_000,
    "max_steps": 20,
    "operation_timeout_seconds": 120,
}


class WorkflowFailure(RuntimeError):
    """Raised when installed behavior violates the declared acceptance."""


def _require(condition: object, message: str) -> None:
    if not condition:
        raise WorkflowFailure(message)


def _mapping(value: object, message: str) -> dict[str, Any]:
    _require(isinstance(value, dict), message)
    return cast(dict[str, Any], value)


def _items(value: object, message: str) -> list[dict[str, Any]]:
    _require(isinstance(value, list), message)
    values = cast(list[object], value)
    _require(all(isinstance(item, dict) for item in values), message)
    return cast(list[dict[str, Any]], values)


def _string(value: object, message: str) -> str:
    _require(isinstance(value, str) and bool(value), message)
    return cast(str, value)


class InstalledRuntime:
    """Invoke one installed Runtime command and retain every exchange."""

    def __init__(
        self,
        command: Path,
        *,
        cwd: Path,
        evidence: Path,
        environment: dict[str, str],
    ) -> None:
        self.command = command
        self.cwd = cwd
        self.evidence = evidence
        self.environment = environment

    def invoke(self, evidence_name: str, *arguments: str) -> dict[str, Any]:
        completed = subprocess.run(  # noqa: S603 - explicit installed command
            (str(self.command), *arguments),
            cwd=self.cwd,
            env=self.environment,
            capture_output=True,
            check=False,
            text=True,
        )
        exchange = {
            "arguments": list(arguments),
            "returncode": completed.returncode,
            "stderr": completed.stderr,
            "stdout": completed.stdout,
        }
        (self.evidence / f"{evidence_name}.exchange.json").write_text(
            json.dumps(exchange, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        _require(
            completed.returncode == 0,
            f"{evidence_name} failed ({completed.returncode}): {completed.stderr}",
        )
        try:
            result = json.loads(completed.stdout)
        except json.JSONDecodeError as exc:
            raise WorkflowFailure(f"{evidence_name} returned non-JSON output") from exc
        result = _mapping(result, f"{evidence_name} returned a non-object")
        (self.evidence / f"{evidence_name}.json").write_text(
            json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
        return result


def _job(
    runtime: InstalledRuntime, evidence_name: str, *arguments: str
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
    job_id = _string(status.get("job_id"), f"{evidence_name} omitted job identity")
    envelope = runtime.invoke(f"{evidence_name}-result", "v2", "result", job_id)
    return status, _mapping(envelope.get("result"), f"{evidence_name} omitted result")


def _terminal(result: dict[str, Any], message: str) -> str:
    identities = result.get("terminal_artifact_ids")
    _require(
        isinstance(identities, list)
        and len(identities) == 1
        and isinstance(identities[0], str),
        message,
    )
    return cast(list[str], identities)[0]


def _artifact_bytes(runtime: InstalledRuntime, artifact_id: str, name: str) -> bytes:
    payload = bytearray()
    offset = 0
    total_bytes: int | None = None
    payload_sha256: str | None = None
    while True:
        page = runtime.invoke(
            f"{name}-page-{offset}",
            "v2",
            "artifact-payload",
            artifact_id,
            "--offset",
            str(offset),
            "--max-bytes",
            str(_PAGE_BYTES),
        )
        total = page.get("total_bytes")
        digest = page.get("payload_sha256")
        _require(isinstance(total, int) and total > 0, f"{name} has invalid size")
        _require(isinstance(digest, str), f"{name} omitted payload digest")
        total_bytes = total if total_bytes is None else total_bytes
        payload_sha256 = digest if payload_sha256 is None else payload_sha256
        _require(total == total_bytes and digest == payload_sha256, f"{name} drifted")
        encoded = _string(page.get("data_base64"), f"{name} omitted page data")
        chunk = base64.b64decode(encoded, validate=True)
        _require(len(chunk) <= _PAGE_BYTES, f"{name} exceeded page bound")
        payload.extend(chunk)
        next_offset = page.get("next_offset")
        if next_offset is None:
            break
        _require(next_offset == offset + len(chunk), f"{name} continuation drifted")
        offset = cast(int, next_offset)
    _require(len(payload) == total_bytes, f"{name} assembled size drifted")
    _require(
        hashlib.sha256(payload).hexdigest() == payload_sha256,
        f"{name} assembled digest drifted",
    )
    return bytes(payload)


def _artifact_json(
    runtime: InstalledRuntime, artifact_id: str, name: str
) -> dict[str, Any]:
    return _mapping(
        json.loads(_artifact_bytes(runtime, artifact_id, name)),
        f"{name} payload is not an object",
    )


def _installed_environment(command: Path) -> dict[str, Any]:
    python = command.parent / "python"
    _require(python.is_file(), "installed command has no sibling Python")
    code = (
        "import importlib.metadata as m,json,sys;"
        "n=('bijux-canon-runtime','bijux-canon-ingest','bijux-canon-index',"
        "'bijux-canon-reason','bijux-canon-agent');"
        "print(json.dumps({'distributions':{x:m.version(x) for x in n},"
        "'executable':sys.executable,'sys_path':sys.path},sort_keys=True))"
    )
    completed = subprocess.run(  # noqa: S603 - resolved sibling interpreter
        (str(python), "-I", "-c", code),
        capture_output=True,
        check=False,
        text=True,
    )
    _require(completed.returncode == 0, "installed metadata inspection failed")
    return _mapping(json.loads(completed.stdout), "installed metadata is invalid")


def _source_hashes(example: Path, manifest: dict[str, Any]) -> set[str]:
    sources = _items(manifest.get("sources"), "manifest sources are invalid")
    _require(len(sources) == manifest.get("source_count") == 4, "source count drifted")
    hashes: set[str] = set()
    formats: set[str] = set()
    for source in sources:
        relative = _string(source.get("local_path"), "source path is missing")
        path = example / relative
        content = path.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        _require(digest == source.get("sha256"), f"source hash drifted: {relative}")
        _require(
            len(content) == source.get("byte_count"), f"source size drifted: {relative}"
        )
        hashes.add(digest)
        formats.add(_string(source.get("format_id"), "source format is missing"))
    _require(formats == {"html", "jats", "markdown", "text"}, "format set drifted")
    return hashes


def _bounded(values: object, *, maximum: int, message: str) -> list[dict[str, Any]]:
    items = _items(values, message)
    _require(len(items) <= maximum, message)
    return items


def _validate_answer(
    runtime: InstalledRuntime,
    *,
    case: dict[str, Any],
    result: dict[str, Any],
    source_hashes: set[str],
) -> dict[str, Any]:
    case_id = _string(case.get("case_id"), "case identity is missing")
    question = _string(case.get("question"), f"{case_id} question is missing")
    output = runtime.invoke(
        f"{case_id}-evaluation",
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
    _require(
        output.get("system_output_may_define_truth") is False,
        f"{case_id} trusts output as truth",
    )
    claims = _items(output.get("claims"), f"{case_id} claims are invalid")
    citations = _items(output.get("citations"), f"{case_id} citations are invalid")
    citation_ids = {
        _string(item.get("citation_id"), "citation identity is missing")
        for item in citations
    }
    for citation in citations:
        exact_text = _string(
            citation.get("exact_text"), f"{case_id} citation text is missing"
        )
        _require(
            hashlib.sha256(exact_text.encode()).hexdigest()
            == citation.get("exact_text_sha256"),
            f"{case_id} citation text hash drifted",
        )
        _require(
            citation.get("source_sha256") in source_hashes,
            f"{case_id} citation source is outside corpus",
        )
    for claim in claims:
        claim_citations = claim.get("citation_ids")
        _require(
            isinstance(claim_citations, list)
            and bool(claim_citations)
            and set(cast(list[str], claim_citations)) <= citation_ids,
            f"{case_id} emitted an unsupported material claim",
        )
    requirements = _mapping(
        case.get("requirements"), f"{case_id} requirements are missing"
    )
    observed_disposition = output.get("disposition")
    expected_disposition = requirements.get("answer_disposition")
    normalized = "abstained" if observed_disposition == "abstained" else "admitted"
    _require(normalized == expected_disposition, f"{case_id} disposition drifted")
    minimum_claims = cast(int, requirements.get("material_claims_min", 0))
    maximum_claims = cast(int, requirements.get("material_claims_max", 1_000_000))
    maximum_citations = cast(int, requirements.get("citation_count_max", 1_000_000))
    minimum_qualified = cast(int, requirements.get("qualified_claims_min", 0))
    _require(
        minimum_claims <= len(claims) <= maximum_claims, f"{case_id} claim count failed"
    )
    _require(len(citations) <= maximum_citations, f"{case_id} citation count failed")
    _require(
        sum(item.get("disposition") == "qualified" for item in claims)
        >= minimum_qualified,
        f"{case_id} qualification requirement failed",
    )
    _require(
        requirements.get("unsupported_material_claims_max") == 0,
        f"{case_id} acceptance permits unsupported claims",
    )
    if citations:
        _require(
            requirements.get("citation_resolution_ratio_min") == 1.0,
            f"{case_id} citation threshold is not strict",
        )
    if normalized == "abstained":
        _require(
            not claims and not citations and output.get("abstention_reason"),
            f"{case_id} abstention leaked claims",
        )
    return {
        "case_id": case_id,
        "citation_count": len(citations),
        "claim_count": len(claims),
        "disposition": normalized,
        "qualified_claim_count": sum(
            item.get("disposition") == "qualified" for item in claims
        ),
        "run_id": result["run_id"],
        "unsupported_material_claims": 0,
    }


def _validate_research(
    runtime: InstalledRuntime,
    *,
    definition: dict[str, Any],
    corpus_id: str,
    index_id: str,
) -> dict[str, Any]:
    case_id = _string(definition.get("case_id"), "research case identity is missing")
    question = _string(definition.get("question"), "research question is missing")
    job, result = _job(
        runtime,
        case_id,
        "research",
        question,
        "--corpus-id",
        corpus_id,
        "--index-id",
        index_id,
        "--top-k",
        "10",
        "--request-id",
        f"request-{case_id}",
        "--idempotency-key",
        case_id,
        "--profile",
        _PROFILE,
        "--operation-timeout-seconds",
        str(_RESEARCH_BUDGET["operation_timeout_seconds"]),
        "--max-artifact-bytes",
        str(_RESEARCH_BUDGET["max_artifact_bytes"]),
        "--max-steps",
        str(_RESEARCH_BUDGET["max_steps"]),
        "--max-provider-tokens",
        str(_RESEARCH_BUDGET["max_provider_tokens"]),
    )
    _require(result.get("status") == "completed", "research did not complete")
    receipt = _artifact_json(
        runtime, _terminal(result, "research omitted receipt"), "research-receipt"
    )
    trace = _artifact_json(
        runtime,
        _string(receipt.get("subject_artifact_id"), "research receipt omitted trace"),
        "research-trace",
    )
    plans = _items(trace.get("targeted_search_plans"), "research plans are invalid")
    classifications = _items(
        trace.get("candidate_classifications"), "research classifications are invalid"
    )
    revision = _mapping(trace.get("answer_revision"), "research revision is missing")
    revised = _mapping(
        revision.get("revised_answer"), "research revised answer is missing"
    )
    presentation = _mapping(
        revised.get("citation_presentation"), "research citations are missing"
    )
    citations = _items(presentation.get("entries"), "research citations are invalid")
    admission = _mapping(revised.get("admission"), "research admission is missing")
    admitted = set(cast(list[str], admission.get("admitted_claim_artifact_ids", [])))
    cited = {
        claim_id
        for citation in citations
        for claim_id in cast(list[str], citation.get("claim_artifact_ids", []))
    }
    termination = _mapping(trace.get("termination"), "research termination is missing")
    reasons = termination.get("reasons")
    requirements = _mapping(
        definition.get("requirements"), "research requirements are missing"
    )
    _require(
        len(plans) >= requirements["distinct_evidence_needs_min"],
        "research evidence needs failed",
    )
    _require(
        len(classifications) >= requirements["candidate_classifications_min"],
        "research classifications failed",
    )
    _require(
        len(citations) >= requirements["citation_count_min"],
        "research citations failed",
    )
    _require(
        admitted and admitted <= cited,
        "research retained an unsupported material claim",
    )
    _require(
        termination.get("stop") is True
        and isinstance(reasons, list)
        and len(reasons) >= requirements["stop_reason_count_min"],
        "research did not stop explicitly",
    )
    limits = _mapping(
        _mapping(trace.get("budget_policy"), "research budget policy is missing").get(
            "global_limits"
        ),
        "research limits are missing",
    )
    usage = _mapping(trace.get("budget_usage"), "research usage is missing")
    _require(
        all(
            isinstance(usage.get(key), int) and usage[key] <= value
            for key, value in limits.items()
        ),
        "research exceeded budget",
    )
    return {
        "candidate_classification_count": len(classifications),
        "citation_count": len(citations),
        "distinct_evidence_need_count": len(plans),
        "job_id": job["job_id"],
        "run_id": result["run_id"],
        "stop_reasons": reasons,
        "unsupported_material_claims": 0,
    }


def _arguments() -> argparse.Namespace:
    example = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-command", default="bijux-canon-runtime")
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--evidence-directory", type=Path, required=True)
    parser.add_argument("--example-directory", type=Path, default=example)
    parser.add_argument(
        "--allow-editable-source",
        action="store_true",
        help="Permit repository source resolution for local runner development only.",
    )
    return parser.parse_args()


def main() -> int:
    """Execute the installed acceptance and emit its compact evidence summary."""
    arguments = _arguments()
    example = arguments.example_directory.resolve()
    sources = example / "corpus" / "sources"
    manifest = _mapping(
        json.loads((example / "corpus-manifest.json").read_text()),
        "manifest is invalid",
    )
    acceptance = _mapping(
        json.loads((example / "acceptance.json").read_text()), "acceptance is invalid"
    )
    _require(
        acceptance.get("system_output_may_define_truth") is False,
        "acceptance trusts system output as truth",
    )
    source_hashes = _source_hashes(example, manifest)
    command_value = shutil.which(arguments.runtime_command) or arguments.runtime_command
    command = Path(command_value).resolve()
    _require(
        command.is_file(), f"runtime command not found: {arguments.runtime_command}"
    )
    workspace = arguments.workspace.resolve()
    evidence = arguments.evidence_directory.resolve()
    _require(not workspace.exists(), "workspace must be new")
    workspace.parent.mkdir(parents=True, exist_ok=True)
    evidence.mkdir(parents=True, exist_ok=True)
    _require(not any(evidence.iterdir()), "evidence directory must be empty")
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    environment.pop("BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH", None)
    environment.update(
        {
            "ALL_PROXY": "http://127.0.0.1:9",
            "HTTP_PROXY": "http://127.0.0.1:9",
            "HTTPS_PROXY": "http://127.0.0.1:9",
            "NO_PROXY": "127.0.0.1,localhost",
            "BIJUX_CANON_RUNTIME_WORKING_ROOT": str(workspace),
        }
    )
    runtime = InstalledRuntime(
        command, cwd=workspace.parent, evidence=evidence, environment=environment
    )
    installed = _installed_environment(command)
    if not arguments.allow_editable_source:
        _require(
            all(
                "/packages/" not in path
                for path in cast(Iterable[str], installed["sys_path"])
            ),
            "installed interpreter resolves repository package source",
        )
    runtime.invoke(
        "workspace-initialization", "init", "--workspace", str(workspace), "--json"
    )
    discovery = runtime.invoke(
        "source-discovery",
        "v2",
        "discover",
        str(sources),
        "--root-name",
        "urban-heat-operations",
    )
    _require(
        discovery.get("complete") is True
        and len(cast(list[object], discovery.get("sources", []))) == 4,
        "source discovery failed",
    )
    _, corpus_result = _job(
        runtime,
        "corpus",
        "ingest",
        str(sources),
        "--request-id",
        "request-urban-heat-ingest",
        "--idempotency-key",
        "urban-heat-ingest",
        "--profile",
        _PROFILE,
    )
    corpus_id = _terminal(corpus_result, "ingest omitted corpus identity")
    corpus = runtime.invoke("corpus-inspection", "v2", "corpus-inspect", corpus_id)
    _require(
        corpus.get("document_count") == 4 and corpus.get("rejection_count") == 0,
        "corpus admission failed",
    )
    _, index_result = _job(
        runtime,
        "index",
        "index",
        corpus_id,
        "--request-id",
        "request-urban-heat-index",
        "--idempotency-key",
        "urban-heat-index",
        "--profile",
        _PROFILE,
    )
    index_id = _terminal(index_result, "index omitted identity")
    index = runtime.invoke("index-inspection", "v2", "index-inspect", index_id)
    _require(
        index.get("backend") == "sqlite-fts5"
        and index.get("chunk_count") == corpus.get("chunk_count"),
        "lexical index failed",
    )
    observations: list[dict[str, Any]] = []
    for case in _items(acceptance.get("cases"), "acceptance cases are invalid"):
        case_id = _string(case.get("case_id"), "case identity is missing")
        question = _string(case.get("question"), f"{case_id} question is missing")
        _, result = _job(
            runtime,
            case_id,
            "ask",
            question,
            "--corpus-id",
            corpus_id,
            "--index-id",
            index_id,
            "--top-k",
            "10",
            "--request-id",
            f"request-{case_id}",
            "--idempotency-key",
            case_id,
            "--profile",
            _PROFILE,
        )
        observations.append(
            _validate_answer(
                runtime, case=case, result=result, source_hashes=source_hashes
            )
        )
    research = _validate_research(
        runtime,
        definition=_mapping(
            acceptance.get("research"), "research acceptance is missing"
        ),
        corpus_id=corpus_id,
        index_id=index_id,
    )
    summary = {
        "acceptance_sha256": hashlib.sha256(
            (example / "acceptance.json").read_bytes()
        ).hexdigest(),
        "cases": observations,
        "corpus": {
            "artifact_id": corpus_id,
            "document_count": corpus["document_count"],
            "format_count": 4,
            "rejection_count": corpus["rejection_count"],
        },
        "corpus_manifest_sha256": hashlib.sha256(
            (example / "corpus-manifest.json").read_bytes()
        ).hexdigest(),
        "index": {
            "artifact_id": index_id,
            "backend": index["backend"],
            "chunk_count": index["chunk_count"],
        },
        "installed_environment": installed,
        "network_isolation": os.environ.get(
            "BIJUX_CANON_NETWORK_ISOLATION", "proxy-denied"
        ),
        "research": research,
        "result": "passed",
        "schema_version": "bijux.canon.example.generalization_workflow.v1",
    }
    (evidence / "summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n", encoding="utf-8"
    )
    print(json.dumps(summary, sort_keys=True))
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, WorkflowFailure, json.JSONDecodeError) as error:
        print(f"generalization workflow failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
