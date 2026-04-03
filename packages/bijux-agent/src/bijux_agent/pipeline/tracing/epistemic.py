"""Epistemic, stop-reason, and fingerprint assertions for traces."""

from __future__ import annotations

from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome
from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.definition import PipelineDefinition
from bijux_agent.pipeline.epistemic import EpistemicVerdict
from bijux_agent.pipeline.results.failure import validate_failure_artifact
from bijux_agent.tracing import RunFingerprint, TraceEntry


def validate(
    final_entry: TraceEntry,
    final_phase: PipelinePhase,
    stop_reason: StopReason | None,
    definition: PipelineDefinition,
) -> None:
    """Validate terminal trace metadata and replay fingerprints."""
    if final_phase == PipelinePhase.ABORTED:
        _validate_abort_entry(final_entry, stop_reason)
    if stop_reason and final_phase != PipelinePhase.ABORTED:
        raise RuntimeError("Provided stop reason without an abort entry")
    if (
        stop_reason
        and stop_reason == StopReason.VERIFICATION_VETO
        and final_phase != PipelinePhase.ABORTED
    ):
        raise RuntimeError("Verification veto must terminate the run")
    if (
        final_phase
        in (
            PipelinePhase.FINALIZE,
            PipelinePhase.DONE,
        )
        and final_entry.decision_artifact is None
    ):
        raise RuntimeError("Finalize entry must include a DecisionArtifact")

    if (
        stop_reason == StopReason.EPISTEMIC_FAILURE
        and final_entry.epistemic_verdict == EpistemicVerdict.CERTAIN
    ):
        raise RuntimeError("Epistemic failures require non-certain verdicts")
    if (
        final_entry.decision_artifact is not None
        and final_entry.decision_artifact.verdict == DecisionOutcome.VETO
        and final_entry.epistemic_verdict == EpistemicVerdict.CERTAIN
    ):
        raise RuntimeError("Veto decisions must surface epistemic uncertainty")
    if final_entry.run_fingerprint:
        _validate_run_fingerprint(final_entry.run_fingerprint, definition)


def _validate_abort_entry(
    entry: TraceEntry,
    stop_reason: StopReason | None,
) -> None:
    if stop_reason is None:
        raise RuntimeError("Abort reason missing for trace ending in ABORTED")
    if entry.stop_reason is None:
        raise RuntimeError("Trace entry for aborted phase missing stop reason")
    if entry.stop_reason != stop_reason:
        raise RuntimeError("Recorded stop reason does not match pipeline exit reason")
    if entry.failure_artifact is None:
        raise RuntimeError("Aborted trace entry must include a FailureArtifact")
    validate_failure_artifact(entry.failure_artifact)
    if entry.failure_artifact.phase != PipelinePhase.ABORTED:
        raise RuntimeError("Failure artifact phase must be ABORTED")


def _validate_run_fingerprint(
    fingerprint: RunFingerprint,
    definition: PipelineDefinition,
) -> None:
    if fingerprint.agent_contract_version != CONTRACT_VERSION:
        raise RuntimeError("Replay fingerprint contract mismatch")
    expected = definition.to_payload()
    if fingerprint.pipeline_definition != expected:
        raise RuntimeError("Replay fingerprint definition mismatch")
