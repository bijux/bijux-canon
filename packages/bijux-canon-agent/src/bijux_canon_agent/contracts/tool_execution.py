"""Typed identities and records for bounded research-tool execution."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import StrEnum
import hashlib
import json
import re
from types import MappingProxyType

from bijux_canon_agent.contracts.tool_policy import (
    ResearchTool,
    ResearchToolOperation,
    ToolInvocation,
    ToolPolicyDecision,
)

_VERSION = re.compile(r"^[1-9][0-9]*\.[0-9]+$")
_ARTIFACT_ID = re.compile(r"^sha256:[0-9a-f]{64}$")
_FORBIDDEN_SUMMARY_TERMS = (
    "api_key",
    "authorization",
    "credential",
    "password",
    "secret",
    "token",
)
_EXPECTED_OPERATIONS = {
    ResearchTool.RETRIEVE: ResearchToolOperation.RETRIEVE,
    ResearchTool.INSPECT: ResearchToolOperation.INSPECT,
    ResearchTool.REASON: ResearchToolOperation.REASON,
    ResearchTool.FILESYSTEM_READ: ResearchToolOperation.READ,
}


def _canonical(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _artifact_id(value: object) -> str:
    return "sha256:" + hashlib.sha256(_canonical(value)).hexdigest()


class ToolReplayPolicy(StrEnum):
    """Permitted behavior when an idempotency identity is repeated."""

    RECORDED_ONLY = "recorded_only"
    IDEMPOTENT_READ = "idempotent_read"


class ToolExecutionStatus(StrEnum):
    """Stable outcomes retained for every registry execution attempt."""

    SUCCEEDED = "succeeded"
    REPLAYED = "replayed"
    INVALID = "invalid"
    CANCELLED = "cancelled"
    TIMED_OUT = "timed_out"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class ResearchToolDescriptor:
    """Versioned schema and authority identity of one registered tool."""

    tool: ResearchTool
    operation: ResearchToolOperation
    version: str
    input_schema_id: str
    output_schema_id: str
    capability: str
    owner_distribution: str
    implementation: str
    replay_policy: ToolReplayPolicy
    cost_units: int
    safe_summary_fields: tuple[str, ...]
    supports_cancellation: bool = True
    read_only: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.tool, ResearchTool):
            raise TypeError("tool descriptor tool must be ResearchTool")
        if not isinstance(self.operation, ResearchToolOperation):
            raise TypeError("tool descriptor operation must be ResearchToolOperation")
        if self.operation is not _EXPECTED_OPERATIONS[self.tool]:
            raise ValueError("tool descriptor operation does not match its tool")
        if not _VERSION.fullmatch(self.version):
            raise ValueError("tool descriptor version must be major.minor")
        for field in (
            "input_schema_id",
            "output_schema_id",
            "capability",
            "owner_distribution",
            "implementation",
        ):
            if not str(getattr(self, field)).strip():
                raise ValueError(f"tool descriptor {field} must not be empty")
        if self.cost_units < 1:
            raise ValueError("tool descriptor cost_units must be positive")
        if not self.safe_summary_fields:
            raise ValueError("tool descriptor requires safe summary fields")
        if tuple(sorted(set(self.safe_summary_fields))) != self.safe_summary_fields:
            raise ValueError("safe summary fields must be sorted and unique")
        if any(
            term in field.casefold()
            for field in self.safe_summary_fields
            for term in _FORBIDDEN_SUMMARY_TERMS
        ):
            raise ValueError("safe summary fields must not name secret material")
        if not self.read_only:
            raise ValueError("research registry admits read-only tools only")
        if not self.supports_cancellation:
            raise ValueError("research registry tools must support cancellation")

    def payload(self) -> dict[str, object]:
        """Return the canonical public registry descriptor."""
        return {
            "tool": self.tool.value,
            "operation": self.operation.value,
            "version": self.version,
            "input_schema_id": self.input_schema_id,
            "output_schema_id": self.output_schema_id,
            "capability": self.capability,
            "owner_distribution": self.owner_distribution,
            "implementation": self.implementation,
            "replay_policy": self.replay_policy.value,
            "cost_units": self.cost_units,
            "safe_summary_fields": list(self.safe_summary_fields),
            "supports_cancellation": self.supports_cancellation,
            "read_only": self.read_only,
        }

    @property
    def artifact_id(self) -> str:
        """Return the content identity of every behavior-bearing field."""
        return _artifact_id(self.payload())


@dataclass(frozen=True, slots=True)
class ToolExecutionRecord:
    """Secret-safe request/result lineage for one registry attempt."""

    artifact_id: str
    sequence: int
    descriptor_artifact_id: str
    policy_decision_artifact_id: str
    request_sha256: str
    result_artifact_id: str | None
    status: ToolExecutionStatus
    safe_summary: Mapping[str, object]
    idempotency_key: str
    replay_source_artifact_id: str | None
    cancellation_artifact_id: str | None
    failure_class: str | None

    def __post_init__(self) -> None:
        if self.sequence < 0:
            raise ValueError("tool execution sequence must not be negative")
        if not isinstance(self.status, ToolExecutionStatus):
            raise TypeError("tool execution status must be ToolExecutionStatus")
        for value, field in (
            (self.descriptor_artifact_id, "descriptor"),
            (self.policy_decision_artifact_id, "policy decision"),
        ):
            if not _ARTIFACT_ID.fullmatch(value):
                raise ValueError(f"tool execution {field} must be an artifact ID")
        if len(self.request_sha256) != 64 or any(
            char not in "0123456789abcdef" for char in self.request_sha256
        ):
            raise ValueError("tool execution request_sha256 must be SHA-256")
        if len(self.idempotency_key) != 64 or any(
            char not in "0123456789abcdef" for char in self.idempotency_key
        ):
            raise ValueError("tool execution idempotency_key must be SHA-256")
        for optional_value, optional_field in (
            (self.result_artifact_id, "result"),
            (self.replay_source_artifact_id, "replay source"),
            (self.cancellation_artifact_id, "cancellation"),
        ):
            if optional_value is not None and not _ARTIFACT_ID.fullmatch(
                optional_value
            ):
                raise ValueError(
                    f"tool execution {optional_field} must be an artifact ID"
                )
        summary = dict(self.safe_summary)
        if any(
            not isinstance(value, str | int | float | bool | type(None))
            or (isinstance(value, str) and (len(value) > 256 or "\n" in value))
            for value in summary.values()
        ):
            raise ValueError("tool execution summary values must be bounded scalars")
        if self.failure_class is not None and (
            len(self.failure_class) > 128
            or re.fullmatch(r"[A-Za-z][A-Za-z0-9_.]*", self.failure_class) is None
        ):
            raise ValueError("tool execution failure_class must be a safe type name")
        if (
            self.status
            in {
                ToolExecutionStatus.SUCCEEDED,
                ToolExecutionStatus.REPLAYED,
            }
            and self.result_artifact_id is None
        ):
            raise ValueError("successful tool execution requires a result identity")
        if self.status is ToolExecutionStatus.REPLAYED and (
            self.replay_source_artifact_id is None
        ):
            raise ValueError("replayed tool execution requires its source record")
        if self.status is ToolExecutionStatus.CANCELLED and (
            self.cancellation_artifact_id is None
        ):
            raise ValueError("cancelled tool execution requires cancellation identity")
        payload = {
            "sequence": self.sequence,
            "descriptor_artifact_id": self.descriptor_artifact_id,
            "policy_decision_artifact_id": self.policy_decision_artifact_id,
            "request_sha256": self.request_sha256,
            "result_artifact_id": self.result_artifact_id,
            "status": self.status.value,
            "safe_summary": summary,
            "idempotency_key": self.idempotency_key,
            "replay_source_artifact_id": self.replay_source_artifact_id,
            "cancellation_artifact_id": self.cancellation_artifact_id,
            "failure_class": self.failure_class,
        }
        if self.artifact_id != _artifact_id(payload):
            raise ValueError("tool execution record identity does not match")
        object.__setattr__(self, "safe_summary", MappingProxyType(summary))

    @classmethod
    def create(
        cls,
        *,
        sequence: int,
        descriptor: ResearchToolDescriptor,
        policy_decision: ToolPolicyDecision,
        invocation: ToolInvocation,
        result_artifact_id: str | None,
        status: ToolExecutionStatus,
        safe_summary: Mapping[str, object],
        replay_source_artifact_id: str | None = None,
        cancellation_artifact_id: str | None = None,
        failure_class: str | None = None,
    ) -> ToolExecutionRecord:
        if result_artifact_id is not None and not _ARTIFACT_ID.fullmatch(
            result_artifact_id
        ):
            raise ValueError("tool result identity must be an artifact ID")
        summary = dict(safe_summary)
        unknown = set(summary).difference(descriptor.safe_summary_fields)
        if unknown:
            raise ValueError("tool summary contains undeclared fields")
        if any(
            term in key.casefold()
            for key in summary
            for term in _FORBIDDEN_SUMMARY_TERMS
        ):
            raise ValueError("tool summary contains a secret-bearing field")
        if len(_canonical(summary)) > 4096:
            raise ValueError("tool summary exceeds the safe bound")
        idempotency_key = invocation.idempotency_key or invocation.request_sha256
        payload = {
            "sequence": sequence,
            "descriptor_artifact_id": descriptor.artifact_id,
            "policy_decision_artifact_id": policy_decision.artifact_id,
            "request_sha256": invocation.request_sha256,
            "result_artifact_id": result_artifact_id,
            "status": status.value,
            "safe_summary": summary,
            "idempotency_key": idempotency_key,
            "replay_source_artifact_id": replay_source_artifact_id,
            "cancellation_artifact_id": cancellation_artifact_id,
            "failure_class": failure_class,
        }
        return cls(
            artifact_id=_artifact_id(payload),
            sequence=sequence,
            descriptor_artifact_id=descriptor.artifact_id,
            policy_decision_artifact_id=policy_decision.artifact_id,
            request_sha256=invocation.request_sha256,
            result_artifact_id=result_artifact_id,
            status=status,
            safe_summary=summary,
            idempotency_key=idempotency_key,
            replay_source_artifact_id=replay_source_artifact_id,
            cancellation_artifact_id=cancellation_artifact_id,
            failure_class=failure_class,
        )


__all__ = [
    "ResearchToolDescriptor",
    "ToolExecutionRecord",
    "ToolExecutionStatus",
    "ToolReplayPolicy",
]
