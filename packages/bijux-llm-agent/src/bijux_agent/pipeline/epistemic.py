"""Epistemic metadata for pipeline verdicts."""

from __future__ import annotations

from enum import StrEnum


class EpistemicVerdict(StrEnum):
    """Describes how confident the pipeline is in its final judgment."""

    CERTAIN = "certain"
    UNCERTAIN = "uncertain"
    CONTRADICTORY = "contradictory"
