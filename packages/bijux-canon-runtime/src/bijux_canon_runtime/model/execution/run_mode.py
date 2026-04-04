# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Execution modes shared across planning, runtime, and persistence."""

from __future__ import annotations

from enum import StrEnum


class RunMode(StrEnum):
    """Execution mode; misuse breaks mode-specific guarantees."""

    PLAN = "plan"
    DRY_RUN = "dry-run"
    LIVE = "live"
    OBSERVE = "observe"
    UNSAFE = "unsafe"


__all__ = ["RunMode"]
