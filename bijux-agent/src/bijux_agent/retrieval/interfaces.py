"""Schemas for retrieval requests/responses and confidence propagation."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib

from pydantic import BaseModel, Field


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
    query: str
    top_k: int = Field(5, ge=1, le=50)
    filters: list[str] = Field(default_factory=list)
    metadata: Mapping[str, str] = Field(default_factory=dict)

    def request_hash(self) -> str:
        digest = hashlib.sha256(self.query.encode("utf-8"))
        digest.update(str(self.top_k).encode("utf-8"))
        return digest.hexdigest()


class RetrievalResponse(BaseModel):
    request_hash: str
    documents: list[RetrievedDocument] = Field(default_factory=list)
    confidence: RetrievalConfidenceEnvelope = Field(
        default_factory=lambda: RetrievalConfidenceEnvelope(overall=0.0)
    )

    def add_document(self, document: RetrievedDocument) -> None:
        self.documents.append(document)
        self.confidence.update(document.id, document.confidence)
