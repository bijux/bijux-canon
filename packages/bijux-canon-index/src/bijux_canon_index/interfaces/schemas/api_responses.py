# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Any

from pydantic import Field

from bijux_canon_index.interfaces.schemas.base import StrictModel


class ListArtifactsResponse(StrictModel):
    artifacts: list[str] = Field(
        description="Execution artifact identifiers available in the active backend."
    )


class ListRunsResponse(StrictModel):
    runs: list[str] = Field(
        description="Recorded execution run identifiers available for inspection."
    )


class CreateResponse(StrictModel):
    name: str = Field(description="Logical corpus name reserved by the API.")
    status: str = Field(
        description="Lifecycle state returned after the create request."
    )


class IngestResponse(StrictModel):
    ingested: int = Field(
        ge=0,
        description="Number of documents accepted into the backend during this call.",
    )
    correlation_id: str = Field(
        description="Correlation identifier attached to the ingest transaction."
    )


class ArtifactResponse(StrictModel):
    artifact_id: str = Field(
        description="Identifier of the execution artifact materialized by the API."
    )
    execution_contract: str = Field(
        description="Execution contract currently attached to the artifact."
    )
    execution_contract_status: str = Field(
        description="Human-readable stability marker for the chosen contract."
    )
    replayable: bool = Field(
        description="Whether the artifact can be replayed under its declared contract."
    )


class ExecuteResponse(StrictModel):
    results: list[str] = Field(
        description="Ordered vector identifiers returned by the execution request."
    )
    correlation_id: str = Field(
        description="Correlation identifier attached to the execution lifecycle."
    )
    execution_contract: str = Field(
        description="Execution contract used to evaluate the query."
    )
    execution_contract_status: str = Field(
        description="Human-readable stability marker for the chosen contract."
    )
    replayable: bool = Field(
        description="Whether the execution result can be replayed faithfully."
    )
    execution_id: str = Field(
        description="Stable execution record identifier written by the run store."
    )


class ExplainResponse(StrictModel):
    document_id: str = Field(description="Document that produced the requested result.")
    chunk_id: str = Field(description="Chunk that contributed the requested result.")
    vector_id: str = Field(description="Vector identifier for the explained result.")
    artifact_id: str = Field(
        description="Execution artifact used to resolve the result."
    )
    metric: str = Field(description="Similarity metric used by the artifact.")
    score: float = Field(description="Score assigned to the result.")
    correlation_id: str = Field(
        description="Correlation identifier of the execution that produced the result."
    )
    execution_contract: str = Field(
        description="Execution contract used by the originating execution."
    )
    execution_contract_status: str = Field(
        description="Human-readable stability marker for the chosen contract."
    )
    replayable: bool = Field(
        description="Whether the explained result belongs to a replayable artifact."
    )
    execution_id: str = Field(
        description="Execution record identifier associated with the explained result."
    )


class ReplayResponse(StrictModel):
    matches: bool = Field(
        description="Whether the replay satisfied the declared equivalence expectation."
    )
    original_fingerprint: str = Field(
        description="Fingerprint recorded for the original execution result."
    )
    replay_fingerprint: str = Field(
        description="Fingerprint computed for the replayed execution result."
    )
    details: dict[str, Any] = Field(
        description="Structured replay diagnostics describing mismatches or checks."
    )
    nondeterministic_sources: list[str] = Field(
        description="Declared or observed non-deterministic sources involved in replay."
    )
    execution_contract: str = Field(
        description="Execution contract enforced during replay."
    )
    execution_contract_status: str = Field(
        description="Human-readable stability marker for the chosen contract."
    )
    replayable: bool = Field(
        description="Whether the original artifact was declared replayable."
    )
    execution_id: str = Field(
        description="Execution record identifier associated with the replay."
    )


__all__ = [
    "ArtifactResponse",
    "CreateResponse",
    "ExecuteResponse",
    "ExplainResponse",
    "IngestResponse",
    "ListArtifactsResponse",
    "ListRunsResponse",
    "ReplayResponse",
]
