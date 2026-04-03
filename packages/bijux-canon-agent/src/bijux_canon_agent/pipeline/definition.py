"""Semantic anchor for declaring pipeline compositions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .control.lifecycle import PIPELINE_LIFECYCLE, PipelineLifecycle

CANONICAL_PIPELINE_NAME = "auditable-doc-pipeline"


@dataclass(frozen=True)
class PipelineDefinition:
    """Barebones structure describing a pipeline's name, phases, and terminals."""

    name: str
    phases: list[PipelineLifecycle]
    terminal_phases: set[PipelineLifecycle]
    allowed_transitions: dict[PipelineLifecycle, set[PipelineLifecycle]] = field(
        default_factory=dict
    )
    skip_reasons: dict[PipelineLifecycle, str] = field(default_factory=dict)

    def to_payload(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "phases": [phase.value for phase in self.phases],
            "terminal_phases": sorted([phase.value for phase in self.terminal_phases]),
            "allowed_transitions": {
                phase.value: sorted([target.value for target in targets])
                for phase, targets in self.allowed_transitions.items()
            },
            "skip_reasons": {
                phase.value: reason for phase, reason in self.skip_reasons.items()
            },
        }


def standard_pipeline_definition() -> PipelineDefinition:
    """Returns the canonical pipeline definition used for validation."""

    return PipelineDefinition(
        name=CANONICAL_PIPELINE_NAME,
        phases=list(PIPELINE_LIFECYCLE),
        terminal_phases={PipelineLifecycle.DONE, PipelineLifecycle.ABORTED},
        allowed_transitions={
            PipelineLifecycle.INIT: {PipelineLifecycle.PLAN},
            PipelineLifecycle.PLAN: {PipelineLifecycle.EXECUTE},
            PipelineLifecycle.EXECUTE: {PipelineLifecycle.JUDGE},
            PipelineLifecycle.JUDGE: {PipelineLifecycle.VERIFY},
            PipelineLifecycle.VERIFY: {PipelineLifecycle.FINALIZE},
            PipelineLifecycle.FINALIZE: {PipelineLifecycle.DONE},
        },
        skip_reasons={
            PipelineLifecycle.INIT: "Initialization handled outside trace",
            PipelineLifecycle.DONE: "Finality implied by FINALIZE",
        },
    )
