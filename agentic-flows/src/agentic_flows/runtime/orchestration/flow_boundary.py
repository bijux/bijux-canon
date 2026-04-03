# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/orchestration/flow_boundary.py."""

from __future__ import annotations

from collections.abc import Callable

from agentic_flows.core.authority import SEMANTICS_SOURCE, SEMANTICS_VERSION
from agentic_flows.runtime.orchestration.determinism_guard import validate_determinism
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps


def enforce_flow_boundary(
    plan: ExecutionSteps,
    *,
    config_validation: Callable[[], None] | None = None,
) -> None:
    """Execute enforce_flow_boundary and enforce its contract."""
    _ = (SEMANTICS_VERSION, SEMANTICS_SOURCE)
    _assert_step_order(plan)
    seed_token = _derive_seed_token(plan)
    validate_determinism(
        environment_fingerprint=plan.environment_fingerprint,
        seed=seed_token,
        unordered_normalized=True,
        determinism_level=plan.determinism_level,
    )
    if config_validation is not None:
        config_validation()


def _derive_seed_token(plan: ExecutionSteps) -> str | None:
    """Internal helper; not part of the public API."""
    if not plan.steps:
        return None
    for step in plan.steps:
        if not step.inputs_fingerprint:
            return None
    return plan.steps[0].inputs_fingerprint


def _assert_step_order(plan: ExecutionSteps) -> None:
    """Internal helper; not part of the public API."""
    for index, step in enumerate(plan.steps):
        if step.step_index != index:
            raise ValueError("execution order must match resolver step order")
