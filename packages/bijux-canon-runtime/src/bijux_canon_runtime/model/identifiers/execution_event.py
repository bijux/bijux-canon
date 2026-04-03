# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/identifiers/execution_event.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.spec.ontology import CausalityTag
from bijux_canon_runtime.spec.ontology.public import EventType


@dataclass(frozen=True)
class ExecutionEvent:
    """Execution event record; misuse breaks trace integrity."""

    spec_version: str
    event_index: int
    step_index: int
    event_type: EventType
    causality_tag: CausalityTag
    timestamp_utc: str
    payload: dict[str, object]
    payload_hash: str


__all__ = ["ExecutionEvent"]
