# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared execution seed helpers for runtime planning and execution."""

from __future__ import annotations

from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps


def derive_seed_token(plan: ExecutionSteps) -> str | None:
    """Derive the deterministic execution seed token from the first complete step."""
    if not plan.steps:
        return None
    for step in plan.steps:
        if not step.inputs_fingerprint:
            return None
    return plan.steps[0].inputs_fingerprint


__all__ = ["derive_seed_token"]
