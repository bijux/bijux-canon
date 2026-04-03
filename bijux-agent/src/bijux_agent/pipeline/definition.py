"""Semantic anchor for declaring pipeline compositions."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from .control.phases import PHASE_SEQUENCE, PipelinePhase

CANONICAL_PIPELINE_NAME = "auditable-doc-pipeline"


@dataclass(frozen=True)
class PipelineDefinition:
    """Barebones structure describing a pipeline's name, phases, and terminals."""

    name: str
    phases: list[PipelinePhase]
    terminal_phases: set[PipelinePhase]
    allowed_transitions: dict[PipelinePhase, set[PipelinePhase]] = field(
        default_factory=dict
    )
    skip_reasons: dict[PipelinePhase, str] = field(default_factory=dict)

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
        phases=list(PHASE_SEQUENCE),
        terminal_phases={PipelinePhase.DONE, PipelinePhase.ABORTED},
        allowed_transitions={
            PipelinePhase.INIT: {PipelinePhase.PLAN},
            PipelinePhase.PLAN: {PipelinePhase.EXECUTE},
            PipelinePhase.EXECUTE: {PipelinePhase.JUDGE},
            PipelinePhase.JUDGE: {PipelinePhase.VERIFY},
            PipelinePhase.VERIFY: {PipelinePhase.FINALIZE},
            PipelinePhase.FINALIZE: {PipelinePhase.DONE},
        },
        skip_reasons={
            PipelinePhase.INIT: "Initialization handled outside trace",
            PipelinePhase.DONE: "Finality implied by FINALIZE",
        },
    )
