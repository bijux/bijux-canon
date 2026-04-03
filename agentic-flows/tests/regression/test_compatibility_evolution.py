# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from agentic_flows.runtime.orchestration.determinism_guard import validate_replay
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.ontology.ids import PlanHash

pytestmark = pytest.mark.regression


def test_allowed_evolution_preserves_replay(resolved_flow, execution_store) -> None:
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    plan = result.resolved_flow.plan
    trace = result.trace

    updated_plan = replace(
        plan,
        resolution_metadata=plan.resolution_metadata + (("doc_text", "note"),),
    )

    validate_replay(trace, updated_plan)


def test_replay_breaker_is_rejected(resolved_flow, execution_store) -> None:
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    plan = result.resolved_flow.plan
    trace = result.trace

    updated_plan = replace(plan, plan_hash=PlanHash("different"))

    with pytest.raises(ValueError, match="plan_hash"):
        validate_replay(trace, updated_plan)
