"""Snapshot and hash helpers for convergence monitoring."""

from __future__ import annotations

from collections.abc import Mapping, Sequence
import hashlib
import json
from typing import Any


def compute_convergence_hash(
    history_window: Sequence[tuple[Mapping[str, float], Any, float]],
) -> str:
    """Compute a deterministic hash for the current convergence window."""
    if not history_window:
        return ""
    normalized: list[tuple[tuple[tuple[str, float], ...], str]] = []
    for scores, verdict, _ in history_window:
        normalized.append((tuple(sorted(scores.items())), verdict.value))
    payload = json.dumps(normalized, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def build_convergence_snapshot(
    *,
    iteration: int,
    confidence: float,
    converged: bool,
    convergence_type: Any,
    convergence_hash: str | None,
    convergence_reason: Any,
) -> dict[str, Any]:
    """Build the persisted convergence snapshot for an iteration."""
    return {
        "iteration": iteration,
        "last_confidence": confidence,
        "converged": converged,
        "convergence_type": convergence_type.value if convergence_type else None,
        "convergence_hash": convergence_hash,
        "convergence_reason": convergence_reason.value if convergence_reason else None,
    }


def build_debug_state(
    *,
    history: Sequence[tuple[Mapping[str, float], Any, float]],
    trace_metadata: Sequence[dict[str, Any]],
    convergence_type: Any,
    convergence_hash: str | None,
    convergence_reason: Any,
) -> dict[str, Any]:
    """Build the debug snapshot exposed by the convergence monitor."""
    return {
        "history": list(history),
        "trace_metadata": list(trace_metadata),
        "convergence_type": convergence_type.value if convergence_type else None,
        "convergence_hash": convergence_hash,
        "convergence_reason": convergence_reason.value if convergence_reason else None,
    }
