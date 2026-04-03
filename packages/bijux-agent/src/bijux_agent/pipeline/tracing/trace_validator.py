"""Validates traces against the canonical pipeline lifecycle."""

from __future__ import annotations

from collections.abc import Sequence

from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.control.stop_conditions import StopReason
from bijux_agent.pipeline.definition import PipelineDefinition
from bijux_agent.pipeline.semantics import PipelineSemantics
from bijux_agent.pipeline.tracing import completeness, epistemic, ordering
from bijux_agent.tracing import ReplayStatus, RunTraceHeader, TraceEntry


class TraceValidator:
    """Ensures runs follow the defined phase order, semantics, and metadata."""

    @staticmethod
    def validate(
        entries: Sequence[TraceEntry],
        definition: PipelineDefinition,
        stop_reason: StopReason | None,
        semantics: dict[PipelinePhase, PipelineSemantics] | None = None,
        header: RunTraceHeader | None = None,
    ) -> None:
        phase_counts, final_entry, final_phase = ordering.validate(
            entries, definition, semantics
        )
        completeness.validate(phase_counts, definition)
        epistemic.validate(final_entry, final_phase, stop_reason, definition)
        _validate_replay_fields(final_entry)
        if not header:
            raise RuntimeError("Trace header required for validation")
        if not header.runtime_version:
            raise RuntimeError("Trace header must include runtime_version")
        if not header.convergence_hash:
            raise RuntimeError(
                "Trace header must include convergence_hash required for replay"
            )
        if not header.model_metadata:
            raise RuntimeError("Trace header must include model metadata")
        _validate_replayability(header)


def _validate_replay_fields(entry: TraceEntry) -> None:
    """Ensure final entries carry replay-critical fields."""

    if not entry.prompt_hash:
        raise RuntimeError("Trace entry missing prompt_hash required for replay")
    if not entry.model_hash:
        raise RuntimeError("Trace entry missing model_hash required for replay")
    fingerprint = entry.run_fingerprint
    if not fingerprint or not fingerprint.fingerprint:
        raise RuntimeError("Trace entry missing run_fingerprint required for replay")
    if (
        entry.phase == PipelinePhase.FINALIZE.value
        and not entry.replay_metadata.convergence_hash
    ):
        raise RuntimeError("Trace entry missing convergence_hash required for replay")


def _validate_replayability(header: RunTraceHeader) -> None:
    """Ensure replayable traces only use deterministic metadata."""

    if header.replay_status != ReplayStatus.REPLAYABLE:
        return
    model_metadata = header.model_metadata
    if model_metadata is None:
        raise RuntimeError("Replayable trace must include model metadata")
    if model_metadata.temperature != 0.0:
        raise RuntimeError(
            "Replayable trace cannot declare non-zero temperature across entries"
        )
