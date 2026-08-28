# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Boundary schemas for persistent immutable index generations."""

from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Self, TypeAlias

from pydantic import Field, model_validator

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexInspectionReport,
    IndexQueryChannel,
    IndexQueryReport,
    IndexQueryRequest,
)
from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
    MetadataOperator,
    UserMetadataPredicate,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters
from bijux_canon_index.interfaces.schemas.base import StrictModel

JsonScalar: TypeAlias = str | int | float | bool | None
MetadataPayload: TypeAlias = JsonScalar | list[str]
PredicatePayload: TypeAlias = str | int | float | bool | list[str | int | float | bool]


class IndexChunkPayload(StrictModel):
    """One exact source chunk and locked-model vector admitted for a build."""

    chunk_id: str = Field(min_length=1)
    document_id: str = Field(min_length=1)
    ordinal: int = Field(ge=0)
    text: str = Field(min_length=1)
    vector: tuple[float, ...] = Field(min_length=1)
    metadata: dict[str, MetadataPayload] = Field(default_factory=dict)

    def to_domain(self) -> AdmittedIndexChunk:
        """Convert validated transport data to the application build contract."""

        return AdmittedIndexChunk(
            chunk_id=self.chunk_id,
            document_id=self.document_id,
            ordinal=self.ordinal,
            text=self.text,
            vector=self.vector,
            metadata={
                key: tuple(value) if isinstance(value, list) else value
                for key, value in self.metadata.items()
            },
        )


class IndexBuildLimitsPayload(StrictModel):
    """Hard build limits supplied through an installed interface."""

    max_chunks: int = Field(gt=0)
    max_text_bytes: int = Field(gt=0)
    max_vector_bytes: int = Field(gt=0)
    max_metadata_bytes: int = Field(gt=0)

    def to_domain(self) -> IndexBuildLimits:
        return IndexBuildLimits(**self.model_dump())


class HnswParametersPayload(StrictModel):
    """Seeded HNSW construction and query parameters."""

    m: int = 32
    ef_construction: int = 200
    ef_search: int = 64
    seed: int = 42

    def to_domain(self) -> HnswParameters:
        return HnswParameters(**self.model_dump())


class IndexBuildRequestPayload(StrictModel):
    """Complete coherent-generation build request."""

    chunks: tuple[IndexChunkPayload, ...] = Field(min_length=1)
    snapshot_artifact_id: str = Field(min_length=1)
    model_lock_artifact_id: str = Field(min_length=1)
    limits: IndexBuildLimitsPayload
    hnsw_parameters: HnswParametersPayload = Field(
        default_factory=HnswParametersPayload
    )
    activate: bool = False


class IndexActivationRequestPayload(StrictModel):
    """Select one already-admitted generation for atomic activation."""

    generation_id: str = Field(min_length=1)


class IndexSelectionPayload(StrictModel):
    """Select an admitted generation, defaulting to the active generation."""

    generation_id: str | None = None


class UserMetadataPredicatePayload(StrictModel):
    """Transport representation of one typed caller-owned metadata predicate."""

    key: str = Field(min_length=1)
    operator: MetadataOperator
    value: PredicatePayload | None = None

    def to_domain(self) -> UserMetadataPredicate:
        value = tuple(self.value) if isinstance(self.value, list) else self.value
        return UserMetadataPredicate(
            key=self.key,
            operator=self.operator,
            value=value,
        )


class MetadataFilterPayload(StrictModel):
    """Full typed metadata filter accepted identically by every channel."""

    source_ids: tuple[str, ...] = ()
    dois: tuple[str, ...] = ()
    paths: tuple[str, ...] = ()
    formats: tuple[str, ...] = ()
    sections: tuple[str, ...] = ()
    date_from: date | None = None
    date_to: date | None = None
    tags: tuple[str, ...] = ()
    languages: tuple[str, ...] = ()
    user: tuple[UserMetadataPredicatePayload, ...] = ()

    def to_domain(self) -> MetadataFilter:
        return MetadataFilter(
            source_ids=self.source_ids,
            dois=self.dois,
            paths=self.paths,
            formats=self.formats,
            sections=self.sections,
            date_from=self.date_from,
            date_to=self.date_to,
            tags=self.tags,
            languages=self.languages,
            user=tuple(predicate.to_domain() for predicate in self.user),
        )


class IndexQueryRequestPayload(StrictModel):
    """Generation query request shared by CLI and HTTP boundaries."""

    generation_id: str | None = None
    channel: IndexQueryChannel
    top_k: int = Field(default=10, ge=1, le=1000)
    query_text: str | None = None
    query_vector: tuple[float, ...] | None = None
    metadata_filter: MetadataFilterPayload | None = None

    @model_validator(mode="after")
    def validate_domain_contract(self) -> Self:
        self.to_domain()
        return self

    def to_domain(self) -> IndexQueryRequest:
        return IndexQueryRequest(
            channel=self.channel,
            top_k=self.top_k,
            query_text=self.query_text,
            query_vector=self.query_vector,
            metadata_filter=(
                None
                if self.metadata_filter is None
                else self.metadata_filter.to_domain()
            ),
        )


class IndexSegmentInspectionPayload(StrictModel):
    stage: str
    backend: str
    item_count: int
    size_bytes: int
    file_sha256: str
    segment_generation_id: str
    chunk_set_sha256: str


class IndexBuildInspectionPayload(StrictModel):
    configuration_id: str
    build_code_id: str
    lexical_algorithm: str
    lexical_schema_version: int
    lexical_tokenizer: str
    lexical_tokenizer_configuration_sha256: str
    dense_exact_algorithm: str
    dense_exact_schema_version: int
    dense_exact_index_type: str
    dense_approximate_algorithm: str
    dense_approximate_schema_version: int
    dense_approximate_index_type: str
    vector_dtype: str
    metric: str
    normalization: str


class IndexFilterInspectionPayload(StrictModel):
    governed_fields: tuple[str, ...]
    user_predicates_supported: bool
    operators: tuple[str, ...]
    applied_at_query_time: bool
    value_payloads_exposed: bool


class IndexLineageInspectionPayload(StrictModel):
    parent_generation_id: str | None
    delta_sha256: str | None
    added: int
    modified: int
    deleted: int
    tombstoned: int


class IndexIntegrityInspectionPayload(StrictModel):
    status: str
    checks: tuple[str, ...]


class IndexActivationInspectionPayload(StrictModel):
    active: bool
    active_generation_id: str | None


class IndexCompatibilityInspectionPayload(StrictModel):
    status: str
    requested_model_lock_artifact_id: str | None
    requested_dimension: int | None
    requested_configuration_id: str | None


class IndexInspectionResponse(StrictModel):
    """Content-safe operational report returned by generation operations."""

    schema_version: str
    generation_id: str
    snapshot_artifact_id: str
    model_lock_artifact_id: str
    chunk_set_sha256: str
    chunk_count: int
    dimension: int
    text_bytes: int
    vector_bytes: int
    metadata_bytes: int
    build: IndexBuildInspectionPayload
    segments: tuple[IndexSegmentInspectionPayload, ...]
    filters: IndexFilterInspectionPayload
    lineage: IndexLineageInspectionPayload
    integrity: IndexIntegrityInspectionPayload
    activation: IndexActivationInspectionPayload
    compatibility: IndexCompatibilityInspectionPayload

    @classmethod
    def from_report(cls, report: IndexInspectionReport) -> IndexInspectionResponse:
        return cls.model_validate(asdict(report))


class IndexQueryHitPayload(StrictModel):
    rank: int
    score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str


class IndexQueryResponse(StrictModel):
    """Normalized content-bound query results from every persistent channel."""

    schema_version: str
    generation_id: str
    channel: IndexQueryChannel
    chunk_set_sha256: str
    hits: tuple[IndexQueryHitPayload, ...]
    authorization_scope_id: str | None = None

    @classmethod
    def from_report(cls, report: IndexQueryReport) -> IndexQueryResponse:
        return cls.model_validate(asdict(report))


__all__ = [
    "HnswParametersPayload",
    "IndexActivationRequestPayload",
    "IndexBuildLimitsPayload",
    "IndexBuildRequestPayload",
    "IndexChunkPayload",
    "IndexInspectionResponse",
    "IndexQueryRequestPayload",
    "IndexQueryResponse",
    "IndexSelectionPayload",
    "MetadataFilterPayload",
    "UserMetadataPredicatePayload",
]
