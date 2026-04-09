# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Tool dispatch helpers."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.types import EvidenceRef, JsonValue, ToolCall, ToolResult
from bijux_canon_reason.execution.evidence_records import write_evidence_record
from bijux_canon_reason.execution.runtime import ExecutionRuntime


@dataclass(frozen=True)
class RetrievedEvidenceRecord:
    """Represents retrieved evidence record."""
    reference: EvidenceRef
    content: bytes


@dataclass(frozen=True)
class ToolDispatchResult:
    """Represents tool dispatch result."""
    retrieval_provenance: dict[str, JsonValue] = field(default_factory=dict)
    evidences: list[RetrievedEvidenceRecord] = field(default_factory=list)
    failures: list[ToolResult] = field(default_factory=list)


def dispatch_tool_requests(
    *,
    node_id: str,
    tool_requests: list[object],
    runtime: ExecutionRuntime,
    push_event: Callable[[dict[str, object]], None],
) -> ToolDispatchResult:
    """Handle dispatch tool requests."""
    retrieval_provenance: dict[str, JsonValue] = {}
    evidences: list[RetrievedEvidenceRecord] = []
    failures: list[ToolResult] = []

    for index, tool_request in enumerate(tool_requests):
        call = ToolCall(
            id=stable_id(
                "call",
                {
                    "step_id": node_id,
                    "i": index,
                    "tool": tool_request.tool_name,
                    "args": tool_request.arguments,
                },
            ),
            tool_name=tool_request.tool_name,
            arguments=dict(tool_request.arguments),
            step_id=node_id,
            call_idx=index,
        )
        push_event(
            {
                "kind": "tool_called",
                "step_id": node_id,
                "call": call.model_dump(mode="json"),
            }
        )
        result = runtime.tools.invoke(call, seed=runtime.seed)
        push_event(
            {
                "kind": "tool_returned",
                "step_id": node_id,
                "result": result.model_dump(mode="json"),
            }
        )
        if not result.success:
            failures.append(result)
            continue
        if (
            tool_request.tool_name == "retrieve"
            and result.success
            and isinstance(result.result, dict)
        ):
            retrieval_provenance = _coerce_provenance(result.result.get("provenance"))
            evidences.extend(
                _extract_retrieved_evidence(
                    runtime=runtime,
                    node_id=node_id,
                    raw=result.result.get("evidences", []),
                    push_event=push_event,
                )
            )

    return ToolDispatchResult(
        retrieval_provenance=retrieval_provenance,
        evidences=evidences,
        failures=failures,
    )


def _coerce_provenance(raw: object) -> dict[str, JsonValue]:
    """Handle coerce provenance."""
    if not isinstance(raw, dict):
        return {}
    provenance: dict[str, JsonValue] = {}
    for key, value in raw.items():
        provenance[str(key)] = value
    return provenance


def _extract_retrieved_evidence(
    *,
    runtime: ExecutionRuntime,
    node_id: str,
    raw: object,
    push_event: Callable[[dict[str, object]], None],
) -> list[RetrievedEvidenceRecord]:
    """Extract retrieved evidence."""
    if not isinstance(raw, list):
        return []

    records: list[RetrievedEvidenceRecord] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        uri = str(item.get("uri", "mem://unknown"))
        text = str(item.get("text", ""))
        chunk_id = str(item.get("chunk_id", ""))
        span = _coerce_span(item.get("span"))
        if span is None or not chunk_id:
            raise RuntimeError(
                "INV-EVD-001: retriever must return chunk span and chunk_id"
            )
        content = text.encode("utf-8")
        evidence = write_evidence_record(
            runtime,
            uri=uri,
            content=content,
            span=span,
            chunk_id=chunk_id,
        )
        push_event(
            {
                "kind": "evidence_registered",
                "step_id": node_id,
                "evidence": evidence.model_dump(mode="json"),
            }
        )
        records.append(RetrievedEvidenceRecord(reference=evidence, content=content))
    return records


def _coerce_span(raw: object) -> tuple[int, int] | None:
    """Handle coerce span."""
    if not isinstance(raw, (list, tuple)) or len(raw) != 2:
        return None
    start, end = raw
    if not isinstance(start, (int, float, str)) or not isinstance(
        end, (int, float, str)
    ):
        return None
    return (int(start), int(end))


__all__ = [
    "RetrievedEvidenceRecord",
    "ToolDispatchResult",
    "dispatch_tool_requests",
]
