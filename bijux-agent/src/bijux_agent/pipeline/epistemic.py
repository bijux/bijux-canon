"""Epistemic metadata for pipeline verdicts."""

from __future__ import annotations

from enum import Enum


class EpistemicVerdict(str, Enum):
    """Describes how confident the pipeline is in its final judgment."""

    CERTAIN = "certain"
    UNCERTAIN = "uncertain"
    CONTRADICTORY = "contradictory"
