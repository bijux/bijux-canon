# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import hashlib
from pathlib import Path
from typing import cast

from bijux_rar.boundaries.serde.json_file import read_json_file
from bijux_rar.boundaries.serde.trace_jsonl import (
    fingerprint_trace_file,
    read_trace_jsonl,
    write_trace_jsonl,
)
from bijux_rar.core.rar_types import (
    JsonValue,
    Plan,
    ProblemSpec,
    ReplayResult,
    RuntimeDescriptor,
    TraceEventKind,
)
from bijux_rar.rar.app import run_app
from bijux_rar.rar.execution.frozen_runtime import RecordedCall
from bijux_rar.rar.execution.runtime import Runtime
from bijux_rar.rar.traces.checksum import compute_invariant_checksum
from bijux_rar.rar.traces.diff import diff_traces


def replay_from_artifacts(trace_path: Path) -> tuple[ReplayResult, Path]:
    run_dir = trace_path.parent
    spec_path = run_dir / "spec.json"
    meta_path = run_dir / "run_meta.json"
    plan_path = run_dir / "plan.json"
    prov_path = run_dir / "provenance" / "retrieval_provenance.json"
    corpus_path = run_dir / "provenance" / "corpus.jsonl"
    index_path = run_dir / "provenance" / "index" / "bm25_index.json"
    replay_dir = run_dir / "replay"
    replay_trace_path = replay_dir / "trace.jsonl"
    replay_dir.mkdir(parents=True, exist_ok=True)

    if not spec_path.exists():
        raise FileNotFoundError(f"Missing spec.json next to trace: {spec_path}")
    if not meta_path.exists():
        raise FileNotFoundError(f"Missing run_meta.json next to trace: {meta_path}")
    if not plan_path.exists():
        raise FileNotFoundError(f"Missing plan.json next to trace: {plan_path}")
    have_prov = prov_path.exists() and corpus_path.exists() and index_path.exists()

    meta = read_json_file(meta_path)
    preset = meta.get("preset", "default")
    seed = int(meta.get("seed", 0))

    spec_raw = read_json_file(spec_path)
    spec_obj = ProblemSpec.model_validate(spec_raw)
    plan_raw = read_json_file(plan_path)
    plan_obj = Plan.model_validate(plan_raw)
    original_trace = read_trace_jsonl(trace_path)
    trace_prov = original_trace.metadata.get("retrieval_provenance")
    if have_prov or isinstance(trace_prov, dict):
        if not isinstance(trace_prov, dict):
            raise ValueError("Trace missing retrieval_provenance metadata")
        if not have_prov:
            raise FileNotFoundError("Missing retrieval provenance artifacts for replay")
        disk_prov = read_json_file(prov_path)
        # Verify hashes match pinned artifacts.
        corpus_bytes = corpus_path.read_bytes()
        index_bytes = index_path.read_bytes()
        corpus_sha = hashlib.sha256(corpus_bytes).hexdigest()
        index_sha = hashlib.sha256(index_bytes).hexdigest()
        for key, expected in [
            ("corpus_sha256", corpus_sha),
            ("index_sha256", index_sha),
        ]:
            recorded = trace_prov.get(key)
            if recorded != expected:
                raise ValueError(
                    f"Provenance mismatch for {key}: {recorded} != {expected}"
                )
        # Config equality check (exact dict match).
        if trace_prov != disk_prov:
            raise ValueError("retrieval_provenance mismatch between trace and disk")
    else:
        # No retrieval provenance: treat as non-retrieval run.
        trace_prov = None

    runtime_info = meta.get("runtime", {})
    runtime_kind = runtime_info.get("kind", "FakeRuntime")
    runtime_mode = runtime_info.get("mode", "live")
    runtime_descriptor_raw = meta.get("runtime_descriptor")
    descriptor_override = (
        None
        if runtime_descriptor_raw is None
        else RuntimeDescriptor.model_validate(runtime_descriptor_raw)
    )

    # Check invariant checksum before replay to ensure artifacts are intact.
    recorded_checksum = meta.get("invariant_checksum") or (
        original_trace.metadata.get("invariant_checksum")
        if isinstance(original_trace.metadata, dict)
        else None
    )
    if recorded_checksum is None:
        raise ValueError("Missing invariant checksum in metadata")
    original_checksum = compute_invariant_checksum(
        plan=plan_obj,
        trace=original_trace,
        runtime_descriptor=descriptor_override,
    )
    if recorded_checksum != original_checksum:
        raise ValueError("INV-DET-001: Invariant checksum mismatch for original trace")

    # Extract recordings from original trace
    recordings: dict[str, RecordedCall] = {}
    for ev in original_trace.events:
        if ev.kind == TraceEventKind.tool_returned and ev.result:
            recordings[ev.result.call_id] = RecordedCall(
                call_id=ev.result.call_id, result=ev.result
            )
    frozen_runtime = Runtime.frozen(
        seed=seed,
        recorded_results={k: v.result for k, v in recordings.items()},
        artifacts_dir=replay_dir,
        descriptors=descriptor_override.tools if descriptor_override else None,
        mode=runtime_mode,
        runtime_kind=runtime_kind,
    )
    replay_result = run_app(
        spec=spec_obj, preset=preset, seed=seed, runtime=frozen_runtime
    )
    replayed = replay_result.trace.model_copy(
        update={"metadata": original_trace.metadata}
    ).with_content_id()
    replay_checksum = compute_invariant_checksum(
        plan=plan_obj,
        trace=replayed,
        runtime_descriptor=descriptor_override,
    )
    if recorded_checksum != replay_checksum:
        raise ValueError(
            "INV-DET-001: Invariant checksum mismatch after replay; artifacts differ from original"
        )
    write_trace_jsonl(replayed, replay_trace_path)
    diff = diff_traces(original_trace, replayed)

    result = ReplayResult(
        original_trace_fingerprint=fingerprint_trace_file(trace_path),
        replayed_trace_fingerprint=fingerprint_trace_file(replay_trace_path),
        diff_summary=cast(dict[str, JsonValue], diff),
    )
    return result, replay_trace_path
