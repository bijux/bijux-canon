# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.boundaries.serde.trace_jsonl import (
    fingerprint_trace_file,
    read_trace_jsonl,
)
from bijux_rar.core.fingerprints import fingerprint_obj
from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.skeleton.run_builder import RunBuilder, RunInputs


def test_run_artifacts_are_versioned_and_fingerprinted(tmp_path: Path) -> None:
    spec = ProblemSpec(
        description="artifact contract test", constraints={}, expected={}
    )
    assert spec.id is not None

    builder = RunBuilder()
    artifacts = builder.build(
        inputs=RunInputs(spec=spec, preset="default", seed=9),
        artifacts_root=tmp_path / "artifacts",
    )

    trace_fp = fingerprint_trace_file(artifacts.trace_path)
    file_fp = artifacts.fingerprint_path.read_text(encoding="utf-8").strip()
    assert trace_fp == file_fp

    import json

    meta_raw = artifacts.run_meta_path.read_text(encoding="utf-8")
    meta = json.loads(meta_raw)
    assert meta["schema_version"] == 1
    assert meta["runtime_fingerprint"]
    assert meta["producer_version"]

    trace = read_trace_jsonl(artifacts.trace_path)
    assert trace.schema_version == 1
    assert trace.fingerprint_algo == "sha256"
    assert trace.canonicalization_version == 1
    assert trace.metadata.get("runtime_fingerprint")

    runtime_fp = fingerprint_obj(artifacts.runtime_descriptor.model_dump(mode="json"))
    assert meta["runtime_fingerprint"] == runtime_fp
    assert artifacts.runtime_descriptor.kind == "FakeRuntime"
