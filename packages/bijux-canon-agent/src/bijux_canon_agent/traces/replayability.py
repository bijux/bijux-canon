"""Helpers for enforcing deterministic trace replay contracts."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.pipeline.control.lifecycle import PipelineLifecycle

REQUIRED_REPLAY_FIELDS = ("input_hash", "config_hash", "model_id")


def resolve_contract_version(metadata: Mapping[str, Any] | None) -> str:
    """Return the trace contract version for a serialized agent output."""
    if not metadata:
        return CONTRACT_VERSION
    return metadata.get("contract_version", CONTRACT_VERSION) or CONTRACT_VERSION


def requires_convergence_hash(*, convergence_hash: str, phase: str | None) -> bool:
    """Return whether the current trace entry must include convergence metadata."""
    return bool(convergence_hash and phase == PipelineLifecycle.FINALIZE.value)


def has_required_replay_metadata(
    replay_metadata: Any,
    *,
    phase: str | None,
    convergence_hash: str,
) -> bool:
    """Validate required deterministic replay metadata."""
    for field_name in REQUIRED_REPLAY_FIELDS:
        if not getattr(replay_metadata, field_name, ""):
            return False
    if getattr(replay_metadata, "model_metadata", None) is None:
        return False
    if requires_convergence_hash(
        convergence_hash=convergence_hash,
        phase=phase,
    ) and not getattr(replay_metadata, "convergence_hash", ""):
        return False
    return True


def enforce_replayable_temperature(
    *,
    temperature: float | None,
    replayable: bool,
) -> None:
    """Reject traces marked replayable when model sampling is non-deterministic."""
    if temperature is not None and temperature > 0 and replayable:
        raise RuntimeError("Trace marked replayable despite non-zero temperature")
