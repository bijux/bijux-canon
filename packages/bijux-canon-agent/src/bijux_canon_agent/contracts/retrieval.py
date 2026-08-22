"""Schemas for retrieval requests/responses and confidence propagation."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field


class RetrievalConfidenceEnvelope(BaseModel):
    overall: float = Field(..., ge=0.0, le=1.0)
    document_confidences: dict[str, float] = Field(default_factory=dict)

    def update(self, doc_id: str, confidence: float) -> None:
        self.document_confidences[doc_id] = confidence
        scores = list(self.document_confidences.values())
        self.overall = sum(scores) / len(scores) if scores else self.overall


class RetrievedDocument(BaseModel):
    id: str
    text: str
    source: str
    confidence: float = Field(..., ge=0.0, le=1.0)
    metadata: Mapping[str, str] = Field(default_factory=dict)


class RetrievalRequest(BaseModel):
    """A retrieval request bound to immutable data generations and policy."""

    model_config = ConfigDict(frozen=True, extra="forbid", str_strip_whitespace=True)

    query: Annotated[str, Field(min_length=1)]
    corpus_generation: Annotated[str, Field(min_length=1)]
    index_generation: Annotated[str, Field(min_length=1)]
    scope: tuple[Annotated[str, Field(min_length=1)], ...] = Field(min_length=1)
    top_k: int = Field(..., ge=1, le=1000)
    retrieval_mode: Literal["lexical", "dense_exact", "dense_approximate", "hybrid"]
    constraints: Mapping[str, Any]
    filters: list[str] = Field(default_factory=list)
    metadata: Mapping[str, str] = Field(default_factory=dict)

    def model_post_init(self, __context: Any) -> None:
        """Reject ambiguous scopes and non-JSON retrieval constraints."""
        if len(self.scope) != len(set(self.scope)):
            raise ValueError("scope entries must be unique")
        try:
            json.dumps(
                dict(self.constraints),
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            )
        except (TypeError, ValueError) as exc:
            raise ValueError("constraints must be canonical JSON values") from exc

    def request_hash(self) -> str:
        """Hash every field that can change retrieval behavior."""
        payload = json.dumps(
            self.model_dump(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        ).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()


class RetrievalResponse(BaseModel):
    request_hash: str
    documents: list[RetrievedDocument] = Field(default_factory=list)
    confidence: RetrievalConfidenceEnvelope = Field(
        default_factory=lambda: RetrievalConfidenceEnvelope(overall=0.0)
    )

    def add_document(self, document: RetrievedDocument) -> None:
        self.documents.append(document)
        self.confidence.update(document.id, document.confidence)
