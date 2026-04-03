'"""Declarative semantics describing what each phase may do."""'

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle


@dataclass(frozen=True)
class PipelineSemantics:
    phase: PipelineLifecycle
    forbidden_artifact_keys: tuple[str, ...] = ()
    forbidden_metadata_keys: tuple[str, ...] = ()
    allow_decision_artifact: bool = False
    allow_epistemic_verdict: bool = False


DEFAULT_PIPELINE_SEMANTICS: dict[PipelineLifecycle, PipelineSemantics] = {
    PipelineLifecycle.PLAN: PipelineSemantics(
        phase=PipelineLifecycle.PLAN,
        forbidden_artifact_keys=("final_result", "final_output"),
        forbidden_metadata_keys=("decision", "finalized"),
    ),
    PipelineLifecycle.EXECUTE: PipelineSemantics(
        phase=PipelineLifecycle.EXECUTE,
        forbidden_metadata_keys=("decision",),
    ),
    PipelineLifecycle.JUDGE: PipelineSemantics(
        phase=PipelineLifecycle.JUDGE,
        forbidden_metadata_keys=("finalized",),
    ),
    PipelineLifecycle.VERIFY: PipelineSemantics(
        phase=PipelineLifecycle.VERIFY,
        forbidden_metadata_keys=("decision", "final_result"),
    ),
    PipelineLifecycle.FINALIZE: PipelineSemantics(
        phase=PipelineLifecycle.FINALIZE,
        allow_decision_artifact=True,
        allow_epistemic_verdict=True,
    ),
}
