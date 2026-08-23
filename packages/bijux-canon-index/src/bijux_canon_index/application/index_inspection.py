# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Content-safe inspection of immutable index generations."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_index.application.index_audit import (
    IndexCompatibility,
    audit_index_generation,
)
from bijux_canon_index.application.index_generation import IndexGeneration
from bijux_canon_index.domain.metadata_filters import (
    GOVERNED_METADATA_FIELDS,
    MetadataOperator,
)


@dataclass(frozen=True, slots=True)
class IndexSegmentInspection:
    """Content-bound identity and resource use for one persistent segment."""

    stage: str
    backend: str
    item_count: int
    size_bytes: int
    file_sha256: str
    segment_generation_id: str
    chunk_set_sha256: str


@dataclass(frozen=True, slots=True)
class IndexBuildInspection:
    """Explicit reproducibility identities bound into the generation."""

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


@dataclass(frozen=True, slots=True)
class IndexFilterInspection:
    """Filter contract shared by every generation segment."""

    governed_fields: tuple[str, ...]
    user_predicates_supported: bool
    operators: tuple[str, ...]
    applied_at_query_time: bool
    value_payloads_exposed: bool


@dataclass(frozen=True, slots=True)
class IndexLineageInspection:
    """Identity and counts for the most recent immutable delta."""

    parent_generation_id: str | None
    delta_sha256: str | None
    added: int
    modified: int
    deleted: int
    tombstoned: int


@dataclass(frozen=True, slots=True)
class IndexIntegrityInspection:
    """Checks completed before an inspection report is returned."""

    status: str
    checks: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class IndexActivationInspection:
    """Activation state observed from one verified registry pointer read."""

    active: bool
    active_generation_id: str | None


@dataclass(frozen=True, slots=True)
class IndexCompatibilityInspection:
    """Compatibility verdict for an optional requested runtime profile."""

    status: str
    requested_model_lock_artifact_id: str | None
    requested_dimension: int | None
    requested_configuration_id: str | None


@dataclass(frozen=True, slots=True)
class IndexInspectionReport:
    """Operational generation facts that exclude text, metadata values, and paths."""

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
    build: IndexBuildInspection
    segments: tuple[IndexSegmentInspection, ...]
    filters: IndexFilterInspection
    lineage: IndexLineageInspection
    integrity: IndexIntegrityInspection
    activation: IndexActivationInspection
    compatibility: IndexCompatibilityInspection


def inspect_index_generation(
    path: str | Path,
    *,
    compatibility: IndexCompatibility | None = None,
    active_generation_id: str | None = None,
) -> IndexInspectionReport:
    """Audit and report one generation without returning stored content or secrets."""

    root = Path(path).resolve()
    audit = audit_index_generation(root, compatibility=compatibility)
    with IndexGeneration.open(root) as generation:
        manifest = generation.manifest
        build_identity = manifest.build_identity
        configuration_id = manifest.configuration_id
        if build_identity is None or configuration_id is None:
            raise ValueError("verified index generation lacks a build identity")
        segments = tuple(
            IndexSegmentInspection(
                stage=receipt.stage,
                backend=receipt.backend,
                item_count=receipt.item_count,
                size_bytes=(root / receipt.file_name).stat().st_size,
                file_sha256=receipt.file_sha256,
                segment_generation_id=receipt.segment_generation_id,
                chunk_set_sha256=receipt.chunk_set_sha256,
            )
            for receipt in manifest.stages
        )
        lineage = manifest.lineage
        statistics = manifest.statistics
        return IndexInspectionReport(
            schema_version="bijux.canon.index.inspection.v1",
            generation_id=manifest.generation_id,
            snapshot_artifact_id=manifest.snapshot_artifact_id,
            model_lock_artifact_id=manifest.model_lock_artifact_id,
            chunk_set_sha256=manifest.chunk_set_sha256,
            chunk_count=statistics.chunk_count,
            dimension=statistics.dimension,
            text_bytes=statistics.text_bytes,
            vector_bytes=statistics.vector_bytes,
            metadata_bytes=statistics.metadata_bytes,
            build=IndexBuildInspection(
                configuration_id=configuration_id,
                build_code_id=build_identity.build_code_id,
                lexical_algorithm=build_identity.lexical_algorithm,
                lexical_schema_version=build_identity.lexical_schema_version,
                lexical_tokenizer=build_identity.lexical_tokenizer,
                lexical_tokenizer_configuration_sha256=(
                    build_identity.lexical_tokenizer_configuration_sha256
                ),
                dense_exact_algorithm=build_identity.dense_exact_algorithm,
                dense_exact_schema_version=(
                    build_identity.dense_exact_schema_version
                ),
                dense_exact_index_type=build_identity.dense_exact_index_type,
                dense_approximate_algorithm=(
                    build_identity.dense_approximate_algorithm
                ),
                dense_approximate_schema_version=(
                    build_identity.dense_approximate_schema_version
                ),
                dense_approximate_index_type=(
                    build_identity.dense_approximate_index_type
                ),
                vector_dtype=build_identity.vector_dtype,
                metric=build_identity.metric,
                normalization=build_identity.normalization,
            ),
            segments=segments,
            filters=IndexFilterInspection(
                governed_fields=GOVERNED_METADATA_FIELDS,
                user_predicates_supported=True,
                operators=tuple(operator.value for operator in MetadataOperator),
                applied_at_query_time=True,
                value_payloads_exposed=False,
            ),
            lineage=IndexLineageInspection(
                parent_generation_id=(
                    None if lineage is None else lineage.parent_generation_id
                ),
                delta_sha256=None if lineage is None else lineage.delta_sha256,
                added=0 if lineage is None else lineage.added,
                modified=0 if lineage is None else lineage.modified,
                deleted=0 if lineage is None else lineage.deleted,
                tombstoned=0 if lineage is None else lineage.tombstoned,
            ),
            integrity=IndexIntegrityInspection(status="verified", checks=audit.checks),
            activation=IndexActivationInspection(
                active=active_generation_id == manifest.generation_id,
                active_generation_id=active_generation_id,
            ),
            compatibility=IndexCompatibilityInspection(
                status="compatible" if compatibility is not None else "not_requested",
                requested_model_lock_artifact_id=(
                    None
                    if compatibility is None
                    else compatibility.model_lock_artifact_id
                ),
                requested_dimension=(
                    None if compatibility is None else compatibility.dimension
                ),
                requested_configuration_id=(
                    None
                    if compatibility is None
                    else compatibility.configuration_id
                ),
            ),
        )


__all__ = [
    "IndexActivationInspection",
    "IndexBuildInspection",
    "IndexCompatibilityInspection",
    "IndexFilterInspection",
    "IndexInspectionReport",
    "IndexIntegrityInspection",
    "IndexLineageInspection",
    "IndexSegmentInspection",
    "inspect_index_generation",
]
