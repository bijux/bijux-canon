# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Replay helpers."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from pathlib import Path
from typing import cast

from bijux_canon_reason.application.run_workflow import run_app
from bijux_canon_reason.core.types import (
    JsonValue,
    Plan,
    ProblemSpec,
    ReplayResult,
    RuntimeDescriptor,
    ToolResult,
    Trace,
    TraceEventKind,
)
from bijux_canon_reason.execution.replay_runtime import RecordedCall
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.interfaces.serialization.json_file import read_json_file
from bijux_canon_reason.interfaces.serialization.trace_jsonl import (
    fingerprint_trace_file,
    read_trace_jsonl,
    write_trace_jsonl,
)
from bijux_canon_reason.traces.checksum import compute_invariant_checksum
from bijux_canon_reason.traces.diff import diff_traces


@dataclass(frozen=True)
class ReplayPaths:
    """Represents replay paths."""
    trace_path: Path
    run_dir: Path
    spec_path: Path
    meta_path: Path
    plan_path: Path
    provenance_path: Path
    corpus_path: Path
    index_path: Path
    replay_dir: Path
    replay_trace_path: Path


@dataclass(frozen=True)
class ReplayInputs:
    """Represents replay inputs."""
    paths: ReplayPaths
    preset: str
    seed: int
    spec: ProblemSpec
    plan: Plan
    trace: Trace
    runtime_kind: str
    runtime_mode: str
    runtime_descriptor: RuntimeDescriptor | None


def replay_from_artifacts(trace_path: Path) -> tuple[ReplayResult, Path]:
    """Handle replay from artifacts."""
    inputs = _load_replay_inputs(trace_path)
    trace = inputs.trace

    # Check invariant checksum before replay to ensure artifacts are intact.
    recorded_checksum = _recorded_checksum(
        meta_path=inputs.paths.meta_path,
        trace=trace,
    )
    original_checksum = compute_invariant_checksum(
        plan=inputs.plan,
        trace=trace,
        runtime_descriptor=inputs.runtime_descriptor,
    )
    if recorded_checksum != original_checksum:
        raise ValueError("INV-DET-001: Invariant checksum mismatch for original trace")

    replay_runtime = Runtime.frozen(
        seed=inputs.seed,
        recorded_results=_collect_recorded_results(trace),
        artifacts_dir=inputs.paths.replay_dir,
        descriptors=(
            inputs.runtime_descriptor.tools if inputs.runtime_descriptor else None
        ),
        mode=inputs.runtime_mode,
        runtime_kind=inputs.runtime_kind,
    )
    replay_result = run_app(
        spec=inputs.spec,
        preset=inputs.preset,
        seed=inputs.seed,
        runtime=replay_runtime,
    )
    replayed = replay_result.trace.model_copy(update={"metadata": trace.metadata})
    replayed = replayed.with_content_id()
    replay_checksum = compute_invariant_checksum(
        plan=inputs.plan,
        trace=replayed,
        runtime_descriptor=inputs.runtime_descriptor,
    )
    if recorded_checksum != replay_checksum:
        raise ValueError(
            "INV-DET-001: Invariant checksum mismatch after replay; artifacts differ from original"
        )
    write_trace_jsonl(replayed, inputs.paths.replay_trace_path)
    diff = diff_traces(trace, replayed)

    result = ReplayResult(
        original_trace_fingerprint=fingerprint_trace_file(inputs.paths.trace_path),
        replayed_trace_fingerprint=fingerprint_trace_file(
            inputs.paths.replay_trace_path
        ),
        diff_summary=cast(dict[str, JsonValue], diff),
    )
    return result, inputs.paths.replay_trace_path


def _load_replay_inputs(trace_path: Path) -> ReplayInputs:
    """Load replay inputs."""
    paths = _build_replay_paths(trace_path)
    _require_replay_artifacts(paths)

    meta = read_json_file(paths.meta_path)
    trace = read_trace_jsonl(paths.trace_path)
    _validate_retrieval_provenance(paths=paths, trace=trace)
    runtime_kind, runtime_mode, runtime_descriptor = _read_runtime_metadata(meta)
    return ReplayInputs(
        paths=paths,
        preset=str(meta.get("preset", "default")),
        seed=int(meta.get("seed", 0)),
        spec=ProblemSpec.model_validate(read_json_file(paths.spec_path)),
        plan=Plan.model_validate(read_json_file(paths.plan_path)),
        trace=trace,
        runtime_kind=runtime_kind,
        runtime_mode=runtime_mode,
        runtime_descriptor=runtime_descriptor,
    )


def _build_replay_paths(trace_path: Path) -> ReplayPaths:
    """Build replay paths."""
    run_dir = trace_path.parent
    replay_dir = run_dir / "replay"
    replay_dir.mkdir(parents=True, exist_ok=True)
    return ReplayPaths(
        trace_path=trace_path,
        run_dir=run_dir,
        spec_path=run_dir / "spec.json",
        meta_path=run_dir / "run_meta.json",
        plan_path=run_dir / "plan.json",
        provenance_path=run_dir / "provenance" / "retrieval_provenance.json",
        corpus_path=run_dir / "provenance" / "corpus.jsonl",
        index_path=run_dir / "provenance" / "index" / "bm25_index.json",
        replay_dir=replay_dir,
        replay_trace_path=replay_dir / "trace.jsonl",
    )


def _require_replay_artifacts(paths: ReplayPaths) -> None:
    """Require replay artifacts."""
    required_paths = (
        ("spec.json", paths.spec_path),
        ("run_meta.json", paths.meta_path),
        ("plan.json", paths.plan_path),
    )
    for artifact_name, artifact_path in required_paths:
        if not artifact_path.exists():
            raise FileNotFoundError(
                f"Missing {artifact_name} next to trace: {artifact_path}"
            )


def _validate_retrieval_provenance(*, paths: ReplayPaths, trace: Trace) -> None:
    """Validate retrieval provenance."""
    trace_provenance = (
        trace.metadata.get("retrieval_provenance")
        if isinstance(trace.metadata, dict)
        else None
    )
    have_artifacts = all(
        artifact.exists()
        for artifact in (paths.provenance_path, paths.corpus_path, paths.index_path)
    )
    if not have_artifacts and not isinstance(trace_provenance, dict):
        return
    if not isinstance(trace_provenance, dict):
        raise ValueError("Trace missing retrieval_provenance metadata")
    if not have_artifacts:
        raise FileNotFoundError("Missing retrieval provenance artifacts for replay")

    pinned_hashes = {
        "corpus_sha256": hashlib.sha256(paths.corpus_path.read_bytes()).hexdigest(),
        "index_sha256": hashlib.sha256(paths.index_path.read_bytes()).hexdigest(),
    }
    for key, expected in pinned_hashes.items():
        recorded = trace_provenance.get(key)
        if recorded != expected:
            raise ValueError(f"Provenance mismatch for {key}: {recorded} != {expected}")

    disk_provenance = read_json_file(paths.provenance_path)
    if trace_provenance != disk_provenance:
        raise ValueError("retrieval_provenance mismatch between trace and disk")


def _read_runtime_metadata(
    meta: dict[str, object],
) -> tuple[str, str, RuntimeDescriptor | None]:
    """Read runtime metadata."""
    runtime_info = meta.get("runtime", {})
    runtime = runtime_info if isinstance(runtime_info, dict) else {}
    descriptor_raw = meta.get("runtime_descriptor")
    descriptor = (
        None
        if descriptor_raw is None
        else RuntimeDescriptor.model_validate(descriptor_raw)
    )
    return (
        str(runtime.get("kind", "FakeRuntime")),
        str(runtime.get("mode", "live")),
        descriptor,
    )


def _recorded_checksum(*, meta_path: Path, trace: Trace) -> str:
    """Handle recorded checksum."""
    meta = read_json_file(meta_path)
    recorded = meta.get("invariant_checksum") or (
        trace.metadata.get("invariant_checksum")
        if isinstance(trace.metadata, dict)
        else None
    )
    if not isinstance(recorded, str) or not recorded:
        raise ValueError("Missing invariant checksum in metadata")
    return recorded


def _collect_recorded_results(trace: Trace) -> dict[str, ToolResult]:
    """Handle collect recorded results."""
    recorded_results: dict[str, ToolResult] = {}
    for event in trace.events:
        if event.kind != TraceEventKind.tool_returned or not event.result:
            continue
        recording = RecordedCall(call_id=event.result.call_id, result=event.result)
        recorded_results[recording.call_id] = recording.result
    return recorded_results
