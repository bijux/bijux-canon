"""Versioned contracts for injected retrieval and reasoning services."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Annotated, Any, Literal, Protocol, runtime_checkable

from pydantic import ConfigDict, Field

from bijux_canon_agent.contracts.base import TypedBaseModel
from bijux_canon_agent.contracts.execution_plan import (
    PlanningBudget,
    ProviderProfile,
)
from bijux_canon_agent.contracts.retrieval import RetrievalRequest


def _canonical_payload(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _require_json(value: object, field_name: str) -> None:
    try:
        _canonical_payload(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must contain canonical JSON values") from exc


class ServicePortDescriptor(TypedBaseModel):
    """Identity of one explicitly constructed installed-package adapter."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    protocol_version: Literal["1.0"] = "1.0"
    port_kind: Literal["retriever", "reasoner"]
    owner_distribution: Literal["bijux-canon-index", "bijux-canon-reason"]
    distribution_version: Annotated[str, Field(min_length=1)]
    implementation_module: Annotated[
        str, Field(pattern=r"^bijux_canon_(?:index|reason)\.[a-zA-Z0-9_.]+$")
    ]
    implementation_name: Annotated[str, Field(min_length=1)]

    def model_post_init(self, __context: Any) -> None:
        expected_owner = {
            "retriever": "bijux-canon-index",
            "reasoner": "bijux-canon-reason",
        }[self.port_kind]
        if self.owner_distribution != expected_owner:
            raise ValueError(f"{self.port_kind} port must be owned by {expected_owner}")


class RetrievalPortResult(TypedBaseModel):
    """Content-addressed retrieval output returned through the Agent port."""

    model_config = ConfigDict(frozen=True, extra="forbid")

    request_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    artifact_id: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    generation_id: Annotated[str, Field(min_length=1)]
    records: tuple[Mapping[str, Any], ...]

    def model_post_init(self, __context: Any) -> None:
        _require_json([dict(record) for record in self.records], "records")


class ReasoningPortRequest(TypedBaseModel):
    """Complete reasoning invocation assembled from plan and retrieval output."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    question: Annotated[str, Field(min_length=1)]
    retrieval: RetrievalPortResult
    constraints: Mapping[str, Any]
    provider_profile: ProviderProfile
    budget: PlanningBudget

    def model_post_init(self, __context: Any) -> None:
        _require_json(dict(self.constraints), "constraints")

    def request_hash(self) -> str:
        """Return the identity of every input visible to the reasoner port."""
        payload = self.model_dump(mode="json")
        return hashlib.sha256(_canonical_payload(payload)).hexdigest()


class ReasoningPortResult(TypedBaseModel):
    """Content-addressed reasoning outcome returned through the Agent port."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    request_sha256: Annotated[str, Field(pattern=r"^[0-9a-f]{64}$")]
    artifact_id: Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")]
    outcome: Literal["answered", "partial", "insufficient", "refused", "failed"]
    text: str | None
    claim_artifact_ids: tuple[
        Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...
    ] = ()
    evidence_artifact_ids: tuple[
        Annotated[str, Field(pattern=r"^sha256:[0-9a-f]{64}$")], ...
    ] = ()
    record: Mapping[str, Any]

    def model_post_init(self, __context: Any) -> None:
        if self.outcome in {"answered", "partial"} and not (self.text or "").strip():
            raise ValueError("answered and partial outcomes require result text")
        if (
            self.outcome in {"insufficient", "refused", "failed"}
            and self.text is not None
        ):
            raise ValueError("non-answer outcomes must not contain result text")
        _require_json(dict(self.record), "record")


@runtime_checkable
class RetrieverPort(Protocol):
    """Agent-owned interface implemented by the Runtime retrieval adapter."""

    @property
    def descriptor(self) -> ServicePortDescriptor: ...

    def retrieve(self, request: RetrievalRequest) -> RetrievalPortResult: ...


@runtime_checkable
class ReasonerPort(Protocol):
    """Agent-owned interface implemented by the Runtime reasoning adapter."""

    @property
    def descriptor(self) -> ServicePortDescriptor: ...

    def reason(self, request: ReasoningPortRequest) -> ReasoningPortResult: ...


__all__ = [
    "ReasonerPort",
    "ReasoningPortRequest",
    "ReasoningPortResult",
    "RetrievalPortResult",
    "RetrieverPort",
    "ServicePortDescriptor",
]
