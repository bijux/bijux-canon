# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Preparation helpers for execution lifecycles."""

from __future__ import annotations

from bijux_canon_runtime.application.flow_boundary import enforce_flow_boundary
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps


def prepare_execution(plan: ExecutionPlan) -> ExecutionSteps:
    """Internal helper; not part of the public API."""
    steps_plan = plan.plan
    enforce_flow_boundary(steps_plan)
    return steps_plan


__all__ = ["prepare_execution"]
