"""Typed cancellation and failure state for bounded research execution."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
from typing import Protocol, runtime_checkable


def _artifact_id(value: object) -> str:
    raw = json.dumps(value, sort_keys=True, separators=(",", ":")).encode()
    return "sha256:" + hashlib.sha256(raw).hexdigest()


@dataclass(frozen=True, slots=True)
class CancellationSignal:
    """Immutable cooperative cancellation state supplied by Runtime."""

    artifact_id: str
    requested: bool
    reason: str | None
    request_artifact_id: str | None

    @classmethod
    def active(cls, *, reason: str, request_artifact_id: str) -> CancellationSignal:
        if not reason.strip():
            raise ValueError("cancellation reason must not be empty")
        if len(request_artifact_id) != 71 or not request_artifact_id.startswith(
            "sha256:"
        ):
            raise ValueError("cancellation request must be an artifact ID")
        payload = {
            "requested": True,
            "reason": reason,
            "request_artifact_id": request_artifact_id,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            requested=True,
            reason=reason,
            request_artifact_id=request_artifact_id,
        )

    @classmethod
    def inactive(cls) -> CancellationSignal:
        payload = {
            "requested": False,
            "reason": None,
            "request_artifact_id": None,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            requested=False,
            reason=None,
            request_artifact_id=None,
        )


@runtime_checkable
class CancellationPort(Protocol):
    """Runtime-owned cooperative cancellation source."""

    def current(self) -> CancellationSignal: ...


class ResearchFailureKind(StrEnum):
    """Stable execution failure classifications."""

    TIMEOUT = "timeout"
    RETRYABLE_TOOL = "retryable_tool"
    PERMANENT_TOOL = "permanent_tool"
    POLICY_DENIED = "policy_denied"


@dataclass(frozen=True, slots=True)
class ResearchFailureRecord:
    """Secret-safe failure state retaining partial evidence lineage."""

    artifact_id: str
    sequence: int
    role: str
    operation: str
    kind: ResearchFailureKind
    retryable: bool
    exception_type: str
    partial_evidence_artifact_ids: tuple[str, ...]

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        role: str,
        operation: str,
        kind: ResearchFailureKind,
        retryable: bool,
        exception_type: str,
        partial_evidence_artifact_ids: tuple[str, ...],
    ) -> ResearchFailureRecord:
        payload = {
            "sequence": sequence,
            "role": role,
            "operation": operation,
            "kind": kind.value,
            "retryable": retryable,
            "exception_type": exception_type,
            "partial_evidence_artifact_ids": list(partial_evidence_artifact_ids),
        }
        return cls(
            artifact_id=_artifact_id(payload),
            sequence=sequence,
            role=role,
            operation=operation,
            kind=kind,
            retryable=retryable,
            exception_type=exception_type,
            partial_evidence_artifact_ids=partial_evidence_artifact_ids,
        )


__all__ = [
    "CancellationPort",
    "CancellationSignal",
    "ResearchFailureKind",
    "ResearchFailureRecord",
]
