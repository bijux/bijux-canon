# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/contracts/execution_plan_contract.py."""

from __future__ import annotations

from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    StepType,
)


def validate(plan: ExecutionPlan) -> None:
    """Validate execution plan; misuse breaks planning guarantees."""
    manifest_agents = set(plan.manifest.agents)
    if plan.plan.dataset != plan.manifest.dataset:
        raise ValueError("execution plan dataset must match manifest")
    if plan.plan.tenant_id != plan.manifest.tenant_id:
        raise ValueError("execution plan tenant_id must match manifest")
    if plan.plan.flow_state != plan.manifest.flow_state:
        raise ValueError("execution plan flow_state must match manifest")
    if plan.plan.replay_mode != plan.manifest.replay_mode:
        raise ValueError("execution plan replay_mode must match manifest")
    if plan.plan.allow_deprecated_datasets != plan.manifest.allow_deprecated_datasets:
        raise ValueError("execution plan allow_deprecated_datasets must match manifest")
    if plan.plan.replay_envelope != plan.manifest.replay_envelope:
        raise ValueError("execution plan replay_envelope must match manifest")
    if plan.plan.entropy_budget != plan.manifest.entropy_budget:
        raise ValueError("execution plan entropy_budget must match manifest")
    if plan.plan.allowed_variance_class != plan.manifest.allowed_variance_class:
        raise ValueError("execution plan allowed_variance_class must match manifest")
    if plan.plan.nondeterminism_intent != plan.manifest.nondeterminism_intent:
        raise ValueError("execution plan nondeterminism_intent must match manifest")
    steps = plan.plan.steps
    step_agents = [step.agent_id for step in steps]
    if len(set(step_agents)) != len(step_agents):
        raise ValueError("resolved steps must be unique per agent")
    if set(step_agents) != manifest_agents:
        raise ValueError("resolved steps must cover all agents exactly once")

    agent_to_index = {step.agent_id: step.step_index for step in steps}
    for step in steps:
        if step.step_type is not StepType.AGENT:
            raise ValueError("executor only supports StepType.AGENT steps")
        if not isinstance(step.determinism_level, DeterminismLevel):
            raise ValueError("resolved step determinism_level must be declared")
        if step.determinism_level != plan.manifest.determinism_level:
            raise ValueError("resolved step determinism_level must match manifest")
        if step.declared_entropy_budget != plan.manifest.entropy_budget:
            raise ValueError("resolved step entropy budget must match manifest")
        if step.allowed_variance_class != plan.manifest.allowed_variance_class:
            raise ValueError("resolved step allowed_variance_class must match manifest")
        if step.nondeterminism_intent != plan.manifest.nondeterminism_intent:
            raise ValueError("resolved step nondeterminism_intent must match manifest")
        for dep in step.declared_dependencies:
            if dep not in agent_to_index:
                raise ValueError("resolved step dependency references unknown agent")
            if agent_to_index[dep] >= step.step_index:
                raise ValueError("dependencies must precede dependent steps")


__all__ = ["validate"]
