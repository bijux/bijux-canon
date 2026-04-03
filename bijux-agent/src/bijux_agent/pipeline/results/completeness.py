"""Ensures traces cover every declared pipeline phase or document skips."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping

from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.definition import PipelineDefinition


class TraceCompletenessCheck:
    """Validates that traced phases align with a pipeline definition."""

    def __init__(self, definition: PipelineDefinition) -> None:
        self.definition = definition

    def validate(self, phase_counts: Mapping[PipelinePhase, int]) -> None:
        counter = Counter(phase_counts)
        order = {phase: idx for idx, phase in enumerate(self.definition.phases)}
        observed_indices = [
            idx for phase, idx in order.items() if counter.get(phase, 0) > 0
        ]
        max_index = max(observed_indices) if observed_indices else -1
        for phase in self.definition.phases:
            count = counter.get(phase, 0)
            index = order[phase]
            if phase in self.definition.skip_reasons:
                if count > 0:
                    raise RuntimeError(
                        f"Phase {phase.value} was explicitly skipped, but entries exist"
                    )
                continue
            if index > max_index:
                if count != 0:
                    raise RuntimeError(
                        f"Phase {phase.value} was recorded even though the run stopped earlier"
                    )
                continue
            if count != 1:
                raise RuntimeError(
                    f"Phase {phase.value} must appear exactly once, found {count}"
                )
