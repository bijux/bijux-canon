# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
from pathlib import Path

import pytest

from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.skeleton.run_builder import RunBuilder, RunInputs
from bijux_rar.rar.traces.replay import replay_from_artifacts


def test_replay_checksum_mismatch_fails(tmp_path: Path) -> None:
    # Build a real run to get invariant_checksum populated.
    spec = ProblemSpec(description="q", constraints={}, expected={}).with_content_id()
    builder = RunBuilder()
    artifacts = builder.build(
        inputs=RunInputs(spec=spec, preset="default", seed=0),
        artifacts_root=tmp_path / "artifacts",
    )

    # Tamper with plan (reorder nodes) to change checksum without updating metadata.
    plan_raw = artifacts.plan.model_dump(mode="json")
    plan_raw["nodes"] = list(reversed(plan_raw.get("nodes", [])))
    (artifacts.run_dir / "plan.json").write_text(
        json.dumps(plan_raw, sort_keys=True), encoding="utf-8"
    )

    # Leave meta/invariant checksum untouched so replay should fail.
    with pytest.raises(ValueError) as exc:
        replay_from_artifacts(artifacts.trace_path)
    assert "INV-DET-001" in str(exc.value)
