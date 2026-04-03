# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.fingerprints import canonical_dumps, fingerprint_bytes
from bijux_rar.core.rar_types import Plan, RuntimeDescriptor, Trace, TraceEventKind


def _evidence_order(trace: Trace) -> list[str]:
    return [
        ev.evidence.id
        for ev in trace.events
        if ev.kind == TraceEventKind.evidence_registered
    ]


def compute_invariant_checksum(
    *,
    plan: Plan,
    trace: Trace,
    runtime_descriptor: RuntimeDescriptor | None = None,
    extra: dict[str, object] | None = None,
) -> str:
    """Deterministic checksum over plan, evidence order, and runtime descriptor."""
    payload: dict[str, object] = {
        "plan": plan.model_dump(mode="json"),
        "evidence_order": _evidence_order(trace),
    }
    if runtime_descriptor is not None:
        payload["runtime_descriptor"] = runtime_descriptor.model_dump(mode="json")
    if extra:
        payload["extra"] = extra
    raw = canonical_dumps(payload).encode("utf-8")
    return fingerprint_bytes(raw)
