# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Execution mode helpers for core logic."""

from __future__ import annotations

from enum import Enum


class ExecutionMode(Enum):
    """Enumeration of execution mode."""
    STRICT = "strict"
    BOUNDED = "bounded"
    EXPLORATORY = "exploratory"


__all__ = ["ExecutionMode"]
