# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Planning phase helpers for LiveExecutor."""

from __future__ import annotations

from agentic_flows.runtime.orchestration.flow_boundary import enforce_flow_boundary
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan


def planning_phase(plan: ExecutionPlan):
    """Internal helper; not part of the public API."""
    steps_plan = plan.plan
    enforce_flow_boundary(steps_plan)
    return steps_plan


__all__ = ["planning_phase"]
