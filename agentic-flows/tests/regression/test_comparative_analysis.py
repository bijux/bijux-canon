# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.observability.analysis.comparative_analysis import (
    compare_runs,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)

pytestmark = pytest.mark.regression


def test_compare_runs_reports_overlap(resolved_flow, execution_store) -> None:
    first = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    second = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    summary = compare_runs([first.trace, second.trace])
    assert summary["runs"] == 2
    assert summary["claim_overlap"] == 1.0
