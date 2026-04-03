"""Completeness guards ensuring traces mention each required phase."""

from __future__ import annotations

from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle
from bijux_canon_agent.pipeline.definition import PipelineDefinition
from bijux_canon_agent.pipeline.results.completeness import TraceCompletenessCheck


def validate(
    phase_counts: dict[PipelineLifecycle, int], definition: PipelineDefinition
) -> None:
    """Assert every expected phase is present according to the definition."""
    TraceCompletenessCheck(definition).validate(phase_counts)
