'"""Declarative semantics describing what each phase may do."""'

from __future__ import annotations

from dataclasses import dataclass

from bijux_agent.pipeline.control.phases import PipelinePhase


@dataclass(frozen=True)
class PipelineSemantics:
    phase: PipelinePhase
    forbidden_artifact_keys: tuple[str, ...] = ()
    forbidden_metadata_keys: tuple[str, ...] = ()
    allow_decision_artifact: bool = False
    allow_epistemic_verdict: bool = False


DEFAULT_PIPELINE_SEMANTICS: dict[PipelinePhase, PipelineSemantics] = {
    PipelinePhase.PLAN: PipelineSemantics(
        phase=PipelinePhase.PLAN,
        forbidden_artifact_keys=("final_result", "final_output"),
        forbidden_metadata_keys=("decision", "finalized"),
    ),
    PipelinePhase.EXECUTE: PipelineSemantics(
        phase=PipelinePhase.EXECUTE,
        forbidden_metadata_keys=("decision",),
    ),
    PipelinePhase.JUDGE: PipelineSemantics(
        phase=PipelinePhase.JUDGE,
        forbidden_metadata_keys=("finalized",),
    ),
    PipelinePhase.VERIFY: PipelineSemantics(
        phase=PipelinePhase.VERIFY,
        forbidden_metadata_keys=("decision", "final_result"),
    ),
    PipelinePhase.FINALIZE: PipelineSemantics(
        phase=PipelinePhase.FINALIZE,
        allow_decision_artifact=True,
        allow_epistemic_verdict=True,
    ),
}
