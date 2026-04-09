# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path
from typing import cast

from bijux_canon_reason.application.run_workflow import run_app
from bijux_canon_reason.core.types import ProblemSpec
from bijux_canon_reason.execution.runtime import ExecutionRuntime, Runtime


def test_run_app_with_fake_runtime(tmp_path: Path) -> None:
    spec = ProblemSpec(description="simple", constraints={}, expected={})
    rt = Runtime.fake(seed=0, artifacts_dir=tmp_path)
    res = run_app(
        spec=spec,
        preset="default",
        seed=0,
        artifacts_dir=tmp_path,
        runtime=cast(ExecutionRuntime, rt),
    )
    assert res.spec.id
    assert res.plan.id
    assert res.trace.id
    assert res.verify_report
