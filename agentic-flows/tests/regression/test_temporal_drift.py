# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.observability.analysis.drift import (
    entropy_drift,
    outcome_drift,
)
from agentic_flows.runtime.observability.analysis.trace_diff import entropy_summary
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)

pytestmark = pytest.mark.regression


def test_temporal_drift_is_within_bounds(resolved_flow, execution_store) -> None:
    first = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    first_summary = entropy_summary(first.trace.entropy_usage)
    first_outcome = {
        "claim_count": len(first.trace.claim_ids),
        "contradiction_count": first.trace.contradiction_count,
        "arbitration_decision": first.trace.arbitration_decision,
    }
    second = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    drift = entropy_drift(
        first_summary,
        entropy_summary(second.trace.entropy_usage),
        max_count_delta=0,
        allow_new_sources=False,
    )
    outcome = outcome_drift(
        first_outcome,
        {
            "claim_count": len(second.trace.claim_ids),
            "contradiction_count": second.trace.contradiction_count,
            "arbitration_decision": second.trace.arbitration_decision,
        },
    )
    assert drift == {}
    assert outcome == {}
