# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/identifiers/agent_invocation.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.ontology.ids import AgentID, InputsFingerprint, VersionID


@dataclass(frozen=True)
class AgentInvocation:
    """Agent invocation record; misuse breaks execution audit."""

    spec_version: str
    agent_id: AgentID
    agent_version: VersionID
    inputs_fingerprint: InputsFingerprint
    declared_outputs: tuple[str, ...]
    execution_mode: str


__all__ = ["AgentInvocation"]
