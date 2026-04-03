# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/identifiers/tool_invocation.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology import DeterminismLevel
from agentic_flows.spec.ontology.ids import ContentHash, ToolID


@dataclass(frozen=True)
class ToolInvocation:
    """Tool invocation record; misuse breaks tool audit."""

    spec_version: str
    tool_id: ToolID
    determinism_level: DeterminismLevel
    inputs_fingerprint: ContentHash
    outputs_fingerprint: ContentHash | None
    duration: float
    outcome: str


__all__ = ["ToolInvocation"]
