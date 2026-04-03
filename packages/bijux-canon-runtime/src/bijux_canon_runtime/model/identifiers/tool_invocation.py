# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/identifiers/tool_invocation.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.ontology import DeterminismLevel
from bijux_canon_runtime.ontology.ids import ContentHash, ToolID


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
