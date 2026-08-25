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
_RUN_ID = re.compile(r"\b(run_v1_[0-9a-f]{64})\b")


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

    def invoke_problem(
        self,
        evidence_name: str,
        *arguments: str,
        environment: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        """Capture one expected public failure without weakening its assertions."""
        completed = subprocess.run(  # noqa: S603 - explicit installed command
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
        _require(completed.returncode != 0, f"{evidence_name} unexpectedly succeeded")
        try:
            value = json.loads(completed.stderr)
        except json.JSONDecodeError as error:
            raise WorkflowFailure(
                f"{evidence_name} did not return a JSON problem"
            ) from error
        value = _mapping(value, f"{evidence_name} returned a non-object problem")
        (self.evidence_directory / f"{evidence_name}.problem.json").write_text(
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


def _compare_configurations(
    runtime: InstalledRuntime,
    *,
    question: str,
    corpus_id: str,
    index_id: str,
    baseline_result: dict[str, Any],
) -> dict[str, Any]:
    job, candidate = _job_result(
        runtime,
        "alternate-answer",
        "ask",
        question,
        "--index-id",
        index_id,
        "--corpus-id",
        corpus_id,
        "--top-k",
        "3",
        "--request-id",
        "request-ancient-dna-offline-answer-top-3",
        "--idempotency-key",
        "ancient-dna-offline-answer-top-3",
        "--profile",
        _PROFILE,
    )
    comparison = runtime.invoke(
        "answer-configuration-comparison",
        "v2",
        "compare",
        _string(baseline_result.get("run_id"), "baseline run identity is missing"),
        _string(candidate.get("run_id"), "candidate run identity is missing"),
        "--baseline-attempt-id",
        _string(
            baseline_result.get("attempt_id"), "baseline attempt identity is missing"
        ),
        "--candidate-attempt-id",
        _string(candidate.get("attempt_id"), "candidate attempt identity is missing"),
        "--dimension",
        "configuration",
    )
    raw_differences = comparison.get("differences")
    _require(
        comparison.get("equivalent") is False
        and isinstance(raw_differences, list)
        and len(raw_differences) == 1,
        "configuration comparison did not expose one material difference",
    )
    difference = _mapping(
        cast(list[object], raw_differences)[0],
        "configuration difference is invalid",
    )
    _require(
        difference.get("dimension") == "configuration"
        and difference.get("classification") == "regression"
        and difference.get("baseline") != difference.get("candidate"),
        "top-k configuration difference was not classified explicitly",
    )
    return {
        "baseline_run_id": baseline_result["run_id"],
        "candidate_job_id": job["job_id"],
        "candidate_run_id": candidate["run_id"],
        "classification": difference["classification"],
        "comparison_sha256": comparison["comparison_sha256"],
        "equivalent": comparison["equivalent"],
    }


def _deliberate_failed_run(
    runtime: InstalledRuntime,
    *,
    missing_source: Path,
) -> dict[str, Any]:
    arguments = (
        "v2",
        "ingest",
        str(missing_source),
        "--request-id",
        "request-ancient-dna-missing-source",
        "--idempotency-key",
        "ancient-dna-missing-source",
        "--profile",
        _PROFILE,
        "--wait",
        "--wait-timeout-seconds",
        "120",
    )
    failed = runtime.invoke("missing-source-run", *arguments)
    _require(
        failed.get("status") == "failed"
        and failed.get("result_available") is False
        and failed.get("error_type") == "RuntimeFirstExecutionError",
        "missing-source run did not retain an explicit failed terminal state",
    )
    retry = runtime.invoke("missing-source-idempotent-retry", *arguments)
    _require(
        retry.get("job_id") == failed.get("job_id")
        and retry.get("status") == "failed"
        and retry.get("attempt_count") == failed.get("attempt_count") == 1,
        "idempotent retry changed the failed job identity or reran it",
    )
    message = _string(failed.get("error_message"), "failed job omitted diagnostics")
    match = _RUN_ID.search(message)
    _require(match is not None, "failed job diagnostics omitted its run identity")
    assert match is not None
    run_id = match.group(1)
    inspection = runtime.invoke(
        "missing-source-run-inspection",
        "v2",
        "inspect",
        run_id,
        "--limit",
        "20",
    )
    counts = _mapping(
        inspection.get("collection_counts"),
        "failed run inspection omitted collection counts",
    )
    _require(
        inspection.get("status") == "failed"
        and inspection.get("provenance", {}).get("parent_job_id")
        == failed.get("job_id")
        and isinstance(counts.get("failures"), int)
        and counts["failures"] > 0,
        "failed run did not retain inspectable causal diagnostics",
    )
    return {
        "attempt_count": failed["attempt_count"],
        "error_type": failed["error_type"],
        "failure_count": counts["failures"],
        "idempotent_retry": True,
        "job_id": failed["job_id"],
        "run_id": run_id,
        "status": failed["status"],
    }


def _backup_restore_lifecycle(
    runtime: InstalledRuntime,
    *,
    workspace: Path,
    answer_job_id: str,
    answer_result: dict[str, Any],
    failed_run: dict[str, Any],
    replay_attempt_id: str,
    replay_job_id: str,
) -> dict[str, Any]:
    backup = runtime.invoke(
        "workspace-backup",
        "v2",
        "backup",
        "offline-lexical-lifecycle",
        "--created-at",
        "2026-08-25T00:00:00+00:00",
    )
    manifest = _mapping(backup.get("manifest"), "backup manifest is missing")
    raw_artifact_ids = manifest.get("artifact_ids")
    _require(
        manifest.get("backup_id") == "offline-lexical-lifecycle"
        and isinstance(raw_artifact_ids, list)
        and raw_artifact_ids,
        "backup omitted its retained artifact inventory",
    )
    artifact_ids = cast(list[str], raw_artifact_ids)
    original_generation = Path(
        _string(backup.get("backup_generation"), "backup generation is missing")
    )
    retired_workspace = workspace.with_name(workspace.name + "-source-unavailable")
    restored_workspace = workspace.with_name(workspace.name + "-restored")
    _require(
        not retired_workspace.exists() and not restored_workspace.exists(),
        "lifecycle fixture destinations must not exist",
    )
    generation_relative = original_generation.relative_to(workspace)
    workspace.rename(retired_workspace)
    _require(not workspace.exists(), "original workspace path remained accessible")
    backup_generation = retired_workspace / generation_relative
    restore = runtime.invoke(
        "workspace-restore",
        "v2",
        "restore",
        str(backup_generation),
        str(restored_workspace),
    )
    _require(
        restore.get("backup_id") == manifest.get("backup_id")
        and restore.get("manifest_sha256") == manifest.get("manifest_sha256")
        and restore.get("artifact_count") == len(artifact_ids)
        and restore.get("inspection_ready") is True
        and restore.get("offline_replay_ready") is True,
        "restored workspace did not retain the verified backup identity",
    )
    restored_environment = dict(runtime.environment)
    restored_environment["BIJUX_CANON_RUNTIME_WORKING_ROOT"] = str(restored_workspace)
    runtime.environment = restored_environment
    restored_readiness = runtime.invoke(
        "restored-readiness",
        "v2",
        "ready",
        "--operation",
        "ask",
        "--profile",
        _PROFILE,
    )
    _require(restored_readiness.get("ready") is True, "restored workspace is not ready")
    answer_status = runtime.invoke(
        "restored-answer-status", "v2", "status", answer_job_id
    )
    answer_envelope = runtime.invoke(
        "restored-answer-result", "v2", "result", answer_job_id
    )
    restored_answer = _mapping(
        answer_envelope.get("result"), "restored answer result is missing"
    )
    failed_status = runtime.invoke(
        "restored-failed-status", "v2", "status", str(failed_run["job_id"])
    )
    prior_replay_status = runtime.invoke(
        "restored-prior-replay-status", "v2", "status", replay_job_id
    )
    _require(
        answer_status.get("status") == "succeeded"
        and restored_answer.get("run_id") == answer_result.get("run_id")
        and failed_status.get("status") == "failed"
        and failed_status.get("error_type") == failed_run.get("error_type")
        and prior_replay_status.get("status") == "succeeded",
        "restored job authority changed a terminal lifecycle identity",
    )
    restored_inspection = runtime.invoke(
        "restored-answer-inspection",
        "v2",
        "inspect",
        str(answer_result["run_id"]),
        "--attempt-id",
        str(answer_result["attempt_id"]),
        "--limit",
        "20",
    )
    _require(
        restored_inspection.get("status") == "completed"
        and restored_inspection.get("selected_attempt_id")
        == answer_result.get("attempt_id"),
        "restored run inspection changed the selected attempt",
    )
    restored_replay_job, restored_replay = _job_result(
        runtime,
        "restored-answer-replay",
        "replay",
        str(answer_result["run_id"]),
        "--source-attempt-id",
        replay_attempt_id,
        "--network-policy",
        "disabled",
        "--request-id",
        "request-ancient-dna-restored-replay",
        "--idempotency-key",
        "ancient-dna-restored-replay",
    )
    _require(
        restored_replay.get("accepted") is True
        and restored_replay.get("exact_artifact_identities") is True,
        "restored strict replay was not exactly accepted",
    )

    manifest_path = restored_workspace / "workspace.json"
    manifest_before = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    mismatched_environment = dict(restored_environment)
    mismatched_environment["BIJUX_CANON_RUNTIME_OFFLINE"] = "0"
    mismatch = runtime.invoke_problem(
        "restored-configuration-mismatch",
        "v2",
        "status",
        answer_job_id,
        environment=mismatched_environment,
    )
    _require(
        mismatch.get("code") == "missing-capability"
        and "incompatible_configuration" in str(mismatch.get("cause"))
        and hashlib.sha256(manifest_path.read_bytes()).hexdigest() == manifest_before,
        "configuration mismatch did not fail before workspace mutation",
    )

    tampered_generation = workspace.parent / "tampered-backup-generation"
    tampered_restore = workspace.parent / "tampered-backup-restore"
    _require(
        not tampered_generation.exists() and not tampered_restore.exists(),
        "tamper fixture destinations must not exist",
    )
    shutil.copytree(backup_generation, tampered_generation)
    digest = artifact_ids[0].removeprefix("sha256:")
    tampered_payload = (
        tampered_generation
        / "cas"
        / "objects"
        / "sha256"
        / digest[:2]
        / digest
        / "payload"
    )
    _require(tampered_payload.is_file(), "tamper fixture payload is missing")
    tampered_payload.unlink()
    tamper_problem = runtime.invoke_problem(
        "tampered-backup-restore",
        "v2",
        "restore",
        str(tampered_generation),
        str(tampered_restore),
    )
    _require(
        tamper_problem.get("code") == "operation-failed"
        and "absent or corrupt" in str(tamper_problem.get("cause"))
        and not tampered_restore.exists()
        and not tampered_restore.with_name(tampered_restore.name + ".partial").exists(),
        "tampered backup did not fail closed without partial activation",
    )
    return {
        "artifact_count": restore["artifact_count"],
        "backup_id": manifest["backup_id"],
        "configuration_mismatch_code": mismatch["code"],
        "failed_job_status": failed_status["status"],
        "manifest_sha256": manifest["manifest_sha256"],
        "original_path_unavailable": not workspace.exists(),
        "restored_replay_attempt_id": restored_replay["replay_attempt_id"],
        "restored_replay_job_id": restored_replay_job["job_id"],
        "restored_root": str(restored_workspace),
        "tampered_restore_code": tamper_problem["code"],
    }


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
    configuration_comparison = _compare_configurations(
        runtime,
        question=args.question,
        corpus_id=corpus_id,
        index_id=index_id,
        baseline_result=answer_result,
    )
    failed_run = _deliberate_failed_run(
        runtime,
        missing_source=workspace.parent / "deliberately-missing-source",
    )
    lifecycle = _backup_restore_lifecycle(
        runtime,
        workspace=workspace,
        answer_job_id=_string(
            answer_job.get("job_id"), "answer job identity is missing"
        ),
        answer_result=answer_result,
        failed_run=failed_run,
        replay_attempt_id=replay_attempt_id,
        replay_job_id=_string(
            replay_job.get("job_id"), "replay job identity is missing"
        ),
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
        "lifecycle": {
            "backup_restore": lifecycle,
            "configuration_comparison": configuration_comparison,
            "failed_run": failed_run,
        },
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
            "restored_root": lifecycle["restored_root"],
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
