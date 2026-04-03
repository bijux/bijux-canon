# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_rar.core.rar_types import ProblemSpec
from bijux_rar.rar.app import run_app
from bijux_rar.rar.execution.runtime import Runtime


def test_run_app_with_fake_runtime(tmp_path: Path) -> None:
    spec = ProblemSpec(description="simple", constraints={}, expected={})
    rt = Runtime.fake(seed=0, artifacts_dir=tmp_path)
    res = run_app(spec=spec, preset="default", seed=0, artifacts_dir=tmp_path, runtime=rt)
    assert res.spec.id
    assert res.plan.id
    assert res.trace.id
    assert res.verify_report
