"""Lifecycle phase markers for agent execution."""

from __future__ import annotations

from enum import StrEnum


class LifecyclePhase(StrEnum):
    """Discrete agent lifecycle checkpoints used for ordering assertions."""

    INIT = "init"
    RUN = "run"
    REVISE = "revise"
    FAIL = "fail"
    SHUTDOWN = "shutdown"
