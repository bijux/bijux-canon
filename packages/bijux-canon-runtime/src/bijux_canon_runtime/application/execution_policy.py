# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Non-determinism policy helpers for runtime execution."""

from __future__ import annotations

from dataclasses import replace

from bijux_canon_runtime.core.errors import NonDeterminismViolationError
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.policy.non_determinism_policy import NonDeterminismPolicy
from bijux_canon_runtime.ontology import EntropyMagnitude
from bijux_canon_runtime.ontology.public import NonDeterminismIntentSource


def ensure_non_determinism_policy(
    resolved_flow: ExecutionPlan,
    config,
):
    """Ensure a runtime execution config has an explicit non-determinism policy."""
    if config.non_determinism_policy is not None:
        return config
    manifest = resolved_flow.manifest
    budget = manifest.entropy_budget
    allowed_variance = (
        manifest.allowed_variance_class or budget.max_magnitude or EntropyMagnitude.LOW
    )
    policy = NonDeterminismPolicy(
        spec_version="v1",
        policy_id="implicit",
        allowed_sources=budget.allowed_sources,
        allowed_intent_sources=(
            NonDeterminismIntentSource.LLM,
            NonDeterminismIntentSource.RETRIEVAL,
            NonDeterminismIntentSource.HUMAN,
            NonDeterminismIntentSource.EXTERNAL,
        ),
        min_entropy_magnitude=budget.min_magnitude,
        max_entropy_magnitude=budget.max_magnitude,
        allowed_variance_class=allowed_variance,
        require_justification=False,
    )
    return replace(config, non_determinism_policy=policy)


def validate_non_determinism_policy(
    resolved_flow: ExecutionPlan,
    config,
) -> None:
    """Validate runtime entropy policy against the resolved manifest budget."""
    policy = config.non_determinism_policy
    if policy is None:
        return
    policy.validate_intents(resolved_flow.manifest.nondeterminism_intent)
    budget = resolved_flow.manifest.entropy_budget
    if any(source not in policy.allowed_sources for source in budget.allowed_sources):
        raise NonDeterminismViolationError(
            "entropy budget includes forbidden entropy sources"
        )
    for slice_budget in budget.per_source:
        if slice_budget.source not in budget.allowed_sources:
            raise NonDeterminismViolationError(
                "entropy budget slice source not in allowed sources"
            )
        if slice_budget.source not in policy.allowed_sources:
            raise NonDeterminismViolationError(
                "entropy budget slice includes forbidden entropy source"
            )
    order = {
        EntropyMagnitude.LOW: 0,
        EntropyMagnitude.MEDIUM: 1,
        EntropyMagnitude.HIGH: 2,
    }
    if order[budget.min_magnitude] < order[policy.min_entropy_magnitude]:
        raise NonDeterminismViolationError(
            "entropy budget minimum below policy minimum"
        )
    if order[budget.max_magnitude] > order[policy.max_entropy_magnitude]:
        raise NonDeterminismViolationError(
            "entropy budget maximum exceeds policy maximum"
        )
    for slice_budget in budget.per_source:
        if order[slice_budget.min_magnitude] < order[policy.min_entropy_magnitude]:
            raise NonDeterminismViolationError(
                "entropy budget slice minimum below policy minimum"
            )
        if order[slice_budget.max_magnitude] > order[policy.max_entropy_magnitude]:
            raise NonDeterminismViolationError(
                "entropy budget slice maximum exceeds policy maximum"
            )
    if resolved_flow.manifest.allowed_variance_class is not None and (
        order[resolved_flow.manifest.allowed_variance_class]
        > order[policy.allowed_variance_class]
    ):
        raise NonDeterminismViolationError(
            "allowed variance class exceeds policy allowance"
        )


__all__ = [
    "ensure_non_determinism_policy",
    "validate_non_determinism_policy",
]
