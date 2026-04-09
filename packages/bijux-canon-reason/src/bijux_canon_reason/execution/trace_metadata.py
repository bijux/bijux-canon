# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Trace metadata helpers."""

from __future__ import annotations

from bijux_canon_reason.core.types import JsonValue, Trace, TraceEvent
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.execution.step_execution import ExecutionState


def build_trace_result(
    *,
    spec_id: str,
    plan_id: str,
    events: list[TraceEvent],
    runtime: Runtime,
    state: ExecutionState,
    min_supports: int,
) -> Trace:
    """Build trace result."""
    trace = Trace(
        id="",
        spec_id=spec_id,
        plan_id=plan_id,
        events=events,
        metadata={
            "run_meta": {
                "seed": runtime.seed,
                "runtime_kind": runtime.runtime_kind,
                "mode": runtime.mode,
            }
        },
    ).with_content_id()
    metadata = dict(trace.metadata)
    metadata["reasoning_policy"] = {"min_supports_per_claim": min_supports}
    if state.retrieval_provenance:
        metadata["retrieval_provenance"] = state.retrieval_provenance
    if state.reasoning_meta:
        reasoning_meta = dict(state.reasoning_meta)
        if "result_sha256" in reasoning_meta:
            reasoning_meta["reasoning_trace_sha256"] = str(
                reasoning_meta["result_sha256"]
            )
        metadata["reasoning_trace"] = _coerce_trace_metadata(reasoning_meta)
    return trace.model_copy(update={"metadata": metadata}).with_content_id()


def _coerce_trace_metadata(value: dict[str, JsonValue]) -> dict[str, JsonValue]:
    """Handle coerce trace metadata."""
    coerced: dict[str, JsonValue] = {}
    for key, item in value.items():
        coerced[str(key)] = item
    return coerced


__all__ = ["build_trace_result"]
