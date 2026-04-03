# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/execution/execution_plan.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.flows.manifest import FlowManifest


@dataclass(frozen=True)
class ExecutionPlan:
    """Resolved execution plan; misuse breaks planning contracts."""

    spec_version: str
    manifest: FlowManifest
    plan: ExecutionSteps


__all__ = ["ExecutionPlan"]
