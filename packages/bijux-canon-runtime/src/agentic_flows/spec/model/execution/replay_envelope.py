# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/replay_envelope.py."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ReplayEnvelope:
    """Immutable at instantiation; any field mutation or threshold edits are forbidden after creation."""

    spec_version: str
    min_claim_overlap: float
    max_contradiction_delta: int


__all__ = ["ReplayEnvelope"]
