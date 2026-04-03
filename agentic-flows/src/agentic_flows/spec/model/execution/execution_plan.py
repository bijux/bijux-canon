# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/execution_plan.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.flow_manifest import FlowManifest


@dataclass(frozen=True)
class ExecutionPlan:
    """Resolved execution plan; misuse breaks planning contracts."""

    spec_version: str
    manifest: FlowManifest
    plan: ExecutionSteps


__all__ = ["ExecutionPlan"]
