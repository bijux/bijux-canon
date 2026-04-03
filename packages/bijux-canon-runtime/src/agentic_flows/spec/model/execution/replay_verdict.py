# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""Module definitions for spec/model/execution/replay_verdict.py."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum


class ReplayVerdict(StrEnum):
    """Replay verdict; misuse breaks replay governance."""

    ACCEPTABLE = "acceptable"
    ACCEPTABLE_WITH_WARNINGS = "acceptable_with_warnings"
    UNACCEPTABLE = "unacceptable"
    NON_CERTIFIABLE = "non_certifiable"


@dataclass(frozen=True)
class ReplayVerdictDetails:
    """Replay verdict detail; misuse breaks auditability."""

    verdict: ReplayVerdict
    details: dict[str, object] = field(default_factory=dict)


__all__ = ["ReplayVerdict", "ReplayVerdictDetails"]
