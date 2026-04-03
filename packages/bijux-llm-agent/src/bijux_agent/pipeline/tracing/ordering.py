"""Rules governing trace phase ordering and agent semantics."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import datetime

from bijux_agent.enums import AgentType
from bijux_agent.pipeline.control.phases import PHASE_DETAILS, PipelinePhase
from bijux_agent.pipeline.definition import PipelineDefinition
from bijux_agent.pipeline.semantics import (
    DEFAULT_PIPELINE_SEMANTICS,
    PipelineSemantics,
)
from bijux_agent.tracing import TraceEntry


def validate(
    entries: Sequence[TraceEntry],
    definition: PipelineDefinition,
    semantics: dict[PipelinePhase, PipelineSemantics] | None = None,
) -> tuple[dict[PipelinePhase, int], TraceEntry, PipelinePhase]:
    """Validate ordering, agent allowances, and semantics for the trace."""
    if not entries:
        raise ValueError("Trace must contain at least one entry")

    phase_order = {phase: idx for idx, phase in enumerate(definition.phases)}
    phase_counts: dict[PipelinePhase, int] = {}
    last_index = -1
    previous_phase: PipelinePhase | None = None
    seen_abort = False
    semantics_map = semantics or DEFAULT_PIPELINE_SEMANTICS
    last_order_key: tuple[int, datetime] | None = None

    for entry in entries:
        phase = _resolve_phase(entry)
        if seen_abort:
            raise RuntimeError("Trace may not continue after an aborted phase")
        order_index = phase_order.get(phase, len(definition.phases))
        timestamp = entry.start_time
        order_key = (order_index, timestamp)
        if last_order_key is not None and order_key < last_order_key:
            raise RuntimeError(
                "Trace entries must be strictly ordered by phase and start_time"
            )
        last_order_key = order_key
        phase_counts[phase] = phase_counts.get(phase, 0) + 1

        if phase in phase_order:
            if order_index < last_index:
                raise RuntimeError(
                    f"Phase {phase.value} recorded after {definition.phases[last_index].value}"
                )
            last_index = order_index
            if (
                previous_phase
                and previous_phase != PipelinePhase.ABORTED
                and previous_phase in definition.allowed_transitions
            ):
                allowed = definition.allowed_transitions[previous_phase]
                if allowed and phase not in allowed:
                    raise RuntimeError(
                        f"Transition from {previous_phase.value} to {phase.value} disallowed"
                    )
        elif phase != PipelinePhase.ABORTED:
            raise RuntimeError(f"Unexpected phase in trace: {phase.value}")

        if phase == PipelinePhase.ABORTED:
            seen_abort = True

        if (
            phase
            not in (
                PipelinePhase.FINALIZE,
                PipelinePhase.DONE,
                PipelinePhase.ABORTED,
                PipelinePhase.INIT,
            )
            and not entry.scores
        ):
            raise RuntimeError(f"Phase {phase.value} requires non-empty scores")

        _validate_agent(entry, phase)
        _validate_semantics(entry, phase, semantics_map.get(phase))
        previous_phase = phase

    final_entry = entries[-1]
    final_phase = _resolve_phase(final_entry)
    return phase_counts, final_entry, final_phase


def _resolve_phase(entry: TraceEntry) -> PipelinePhase:
    phase_value = entry.phase or entry.input.get("phase")
    if not phase_value:
        raise RuntimeError("Trace entry missing phase information")
    try:
        return PipelinePhase(phase_value)
    except ValueError as exc:  # pragma: no cover - defensive
        raise RuntimeError(f"Unknown phase recorded: {phase_value}") from exc


def _validate_agent(entry: TraceEntry, phase: PipelinePhase) -> None:
    info = PHASE_DETAILS.get(phase)
    agent_type_value = entry.input.get("agent_type")
    if info and info.allowed_agents and agent_type_value:
        try:
            agent_type = AgentType(agent_type_value)
        except ValueError as exc:
            raise RuntimeError(f"Unknown agent type: {agent_type_value}") from exc
        if agent_type not in info.allowed_agents:
            raise RuntimeError(f"Agent {agent_type.value} not allowed in {phase.value}")


def _validate_semantics(
    entry: TraceEntry,
    phase: PipelinePhase,
    semantics: PipelineSemantics | None,
) -> None:
    if semantics is None:
        return
    artifacts = (entry.output or {}).get("artifacts", {})
    metadata = (entry.output or {}).get("metadata", {})
    for key in semantics.forbidden_artifact_keys:
        if key in artifacts:
            raise RuntimeError(f"Phase {phase.value} must not emit artifact {key}")
    for key in semantics.forbidden_metadata_keys:
        if key in metadata:
            raise RuntimeError(f"Phase {phase.value} must not publish metadata {key}")
    if not semantics.allow_decision_artifact and entry.decision_artifact is not None:
        raise RuntimeError(f"Phase {phase.value} may not carry a DecisionArtifact")
    if not semantics.allow_epistemic_verdict and entry.epistemic_verdict is not None:
        raise RuntimeError(f"Phase {phase.value} may not carry an EpistemicVerdict")
