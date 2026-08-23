# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical application service for immutable index generation operations."""

from __future__ import annotations

from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from enum import StrEnum
import hashlib
from pathlib import Path
import tempfile
import threading
from time import perf_counter

from bijux_canon_index.application.index_activation import IndexGenerationRegistry
from bijux_canon_index.application.index_archive import (
    IndexGenerationArchive,
    admit_index_generation_archive,
    export_index_generation,
)
from bijux_canon_index.application.index_audit import IndexCompatibility
from bijux_canon_index.application.index_generation import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexGeneration,
)
from bijux_canon_index.application.index_inspection import IndexInspectionReport
from bijux_canon_index.application.index_resource_cache import (
    IndexGenerationResourceCache,
    IndexResourceCacheReport,
)
from bijux_canon_index.application.vex.witnesses import (
    ExactSearchWitness,
    build_exact_search_witness,
)
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters


class IndexQueryChannel(StrEnum):
    """Persistent retrieval channel selected for one query."""

    lexical = "sqlite-fts5"
    dense_exact = "faiss-flat-ip"
    dense_hnsw = "faiss-hnsw"


@dataclass(frozen=True, slots=True)
class IndexQueryRequest:
    """Transport-neutral query admitted by the index application service."""

    channel: IndexQueryChannel
    top_k: int
    query_text: str | None = None
    query_vector: Sequence[float] | None = None
    metadata_filter: MetadataFilter | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.channel, IndexQueryChannel):
            raise ValueError("index query channel is unsupported")
        if not 1 <= self.top_k <= 1000:
            raise ValueError("top_k must be between 1 and 1000")
        if self.channel is IndexQueryChannel.lexical:
            if self.query_text is None or not self.query_text.strip():
                raise ValueError("lexical queries require non-empty query text")
            if self.query_vector is not None:
                raise ValueError("lexical queries must not contain a query vector")
            return
        if self.query_text is not None:
            raise ValueError("dense queries must not contain query text")
        if self.query_vector is None:
            raise ValueError("dense queries require a query vector")


@dataclass(frozen=True, slots=True)
class IndexQueryHit:
    """Content-bound locator returned consistently by every retrieval channel."""

    rank: int
    score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str


@dataclass(frozen=True, slots=True)
class IndexQueryReport:
    """Normalized results from one verified immutable generation."""

    schema_version: str
    generation_id: str
    channel: IndexQueryChannel
    chunk_set_sha256: str
    hits: tuple[IndexQueryHit, ...]


class IndexPreparationCacheStatus(StrEnum):
    """Whether archive admission was required for one retrieval request."""

    cold = "cold"
    warm = "warm"
    invalidated = "invalidated"


@dataclass(frozen=True, slots=True)
class PreparedIndexGeneration:
    """One active generation plus observable cache and admission evidence."""

    schema_version: str
    inspection: IndexInspectionReport
    archive_content_sha256: str
    cache_status: IndexPreparationCacheStatus
    preparation_ms: float
    resource_cache: IndexResourceCacheReport


class IndexService:
    """Own build, activation, inspection, verification, and query behavior."""

    def __init__(
        self,
        registry_root: str | Path,
        *,
        compatibility: IndexCompatibility | None = None,
        resource_cache: IndexGenerationResourceCache | None = None,
    ) -> None:
        resolved_root = Path(registry_root).resolve()
        self._resource_cache = resource_cache or IndexGenerationResourceCache(
            cache_identity=(
                "sha256:"
                + hashlib.sha256(str(resolved_root).encode("utf-8")).hexdigest()
            )
        )
        self._registry = IndexGenerationRegistry(
            resolved_root,
            compatibility=compatibility,
            resource_cache=self._resource_cache,
        )
        self._preparation_lock = threading.Lock()
        self._prepared_archive: tuple[str, IndexInspectionReport] | None = None

    @property
    def registry_root(self) -> Path:
        """Return the configured operator-owned registry root."""

        return Path(self._registry.root)

    @property
    def resource_cache(self) -> IndexGenerationResourceCache:
        """Return the cache shared by every service in this process lifecycle."""

        return self._resource_cache

    def build(
        self,
        chunks: Iterable[AdmittedIndexChunk],
        *,
        snapshot_artifact_id: str,
        model_lock_artifact_id: str,
        limits: IndexBuildLimits,
        hnsw_parameters: HnswParameters | None = None,
        activate: bool = False,
    ) -> IndexInspectionReport:
        """Build, admit, optionally activate, and report one coherent generation."""

        with (
            tempfile.TemporaryDirectory(
                prefix=".generation-building-",
                dir=self._registry.root,
            ) as work,
            IndexGeneration.build(
                Path(work) / "generation",
                chunks,
                snapshot_artifact_id=snapshot_artifact_id,
                model_lock_artifact_id=model_lock_artifact_id,
                limits=limits,
                hnsw_parameters=hnsw_parameters,
            ) as generation,
        ):
            generation_id = self._registry.admit(generation.path)
        if activate:
            self._registry.activate(generation_id)
        return self._registry.inspect(generation_id)

    def build_from_lexical(
        self,
        lexical_segment_path: str | Path,
        chunks: Iterable[AdmittedIndexChunk],
        *,
        snapshot_artifact_id: str,
        model_lock_artifact_id: str,
        limits: IndexBuildLimits,
        hnsw_parameters: HnswParameters | None = None,
        activate: bool = False,
    ) -> IndexInspectionReport:
        """Build and admit dense indexes around a completed lexical segment."""

        with (
            tempfile.TemporaryDirectory(
                prefix=".generation-building-",
                dir=self._registry.root,
            ) as work,
            IndexGeneration.build_from_lexical(
                Path(work) / "generation",
                lexical_segment_path,
                chunks,
                snapshot_artifact_id=snapshot_artifact_id,
                model_lock_artifact_id=model_lock_artifact_id,
                limits=limits,
                hnsw_parameters=hnsw_parameters,
            ) as generation,
        ):
            generation_id = self._registry.admit(generation.path)
        if activate:
            self._registry.activate(generation_id)
        return self._registry.inspect(generation_id)

    def activate(self, generation_id: str) -> IndexInspectionReport:
        """Atomically activate and report one admitted generation."""

        self._registry.activate(generation_id)
        return self._registry.inspect(generation_id)

    def export(self, generation_id: str) -> IndexGenerationArchive:
        """Return a portable archive containing the complete generation payload."""

        return export_index_generation(self.registry_root, generation_id)

    def admit_archive(
        self,
        content: bytes,
        *,
        activate: bool = False,
    ) -> IndexInspectionReport:
        """Verify and admit a complete generation from portable canonical bytes."""

        return admit_index_generation_archive(
            self.registry_root,
            content,
            activate=activate,
            resource_cache=self._resource_cache,
        )

    def prepare_archive(self, content: bytes) -> PreparedIndexGeneration:
        """Admit and activate changed content once, then reuse its exact identity."""

        archive_sha256 = hashlib.sha256(content).hexdigest()
        started = perf_counter()
        with self._preparation_lock:
            prepared = self._prepared_archive
            if prepared is not None and prepared[0] == archive_sha256:
                active = self._registry.active_generation_id(required=False)
                if active == prepared[1].generation_id:
                    status = IndexPreparationCacheStatus.warm
                    inspection = prepared[1]
                else:
                    status = IndexPreparationCacheStatus.invalidated
                    inspection = self.admit_archive(content, activate=True)
                    self._prepared_archive = (archive_sha256, inspection)
            else:
                status = (
                    IndexPreparationCacheStatus.cold
                    if prepared is None
                    else IndexPreparationCacheStatus.invalidated
                )
                inspection = self.admit_archive(content, activate=True)
                self._prepared_archive = (archive_sha256, inspection)
        return PreparedIndexGeneration(
            schema_version="bijux.canon.index.prepared_generation.v1",
            inspection=inspection,
            archive_content_sha256=archive_sha256,
            cache_status=status,
            preparation_ms=(perf_counter() - started) * 1000.0,
            resource_cache=self._resource_cache.report(),
        )

    def inspect(self, generation_id: str | None = None) -> IndexInspectionReport:
        """Return a content-safe report for one admitted generation."""

        return self._registry.inspect(generation_id)

    def verify(self, generation_id: str | None = None) -> IndexInspectionReport:
        """Run all integrity and compatibility checks and return their report."""

        return self._registry.inspect(generation_id)

    def query(
        self,
        request: IndexQueryRequest,
        *,
        generation_id: str | None = None,
    ) -> IndexQueryReport:
        """Query one verified generation through a normalized application contract."""

        with self._registry.lease(generation_id) as generation:
            chunks = {chunk.chunk_id: chunk for chunk in generation.lexical.chunks()}
            if request.channel is IndexQueryChannel.lexical:
                assert request.query_text is not None
                raw_hits = generation.lexical.query(
                    request.query_text,
                    top_k=request.top_k,
                    metadata_filter=request.metadata_filter,
                )
                hits = tuple(
                    IndexQueryHit(
                        rank=hit.rank,
                        score=hit.score,
                        chunk_id=hit.chunk.chunk_id,
                        document_id=hit.chunk.document_id,
                        ordinal=hit.chunk.ordinal,
                        source_text_sha256=_text_sha256(hit.chunk.text),
                    )
                    for hit in raw_hits
                )
            else:
                assert request.query_vector is not None
                dense_hits = (
                    generation.exact.query(
                        request.query_vector,
                        top_k=request.top_k,
                        metadata_filter=request.metadata_filter,
                    )
                    if request.channel is IndexQueryChannel.dense_exact
                    else generation.hnsw.query(
                        request.query_vector,
                        top_k=request.top_k,
                        metadata_filter=request.metadata_filter,
                    )
                )
                hits = tuple(
                    IndexQueryHit(
                        rank=hit.rank,
                        score=hit.score,
                        chunk_id=hit.chunk_id,
                        document_id=chunks[hit.chunk_id].document_id,
                        ordinal=chunks[hit.chunk_id].ordinal,
                        source_text_sha256=_text_sha256(chunks[hit.chunk_id].text),
                    )
                    for hit in dense_hits
                )
            return IndexQueryReport(
                schema_version="bijux.canon.index.query.v1",
                generation_id=generation.manifest.generation_id,
                channel=request.channel,
                chunk_set_sha256=generation.manifest.chunk_set_sha256,
                hits=hits,
            )

    def exact_witness(
        self,
        request: IndexQueryRequest,
        *,
        generation_id: str | None = None,
    ) -> ExactSearchWitness:
        """Build an exact reference ranking for one admitted dense query."""

        if request.channel is IndexQueryChannel.lexical:
            raise ValueError("exact witnesses require a dense query")
        assert request.query_vector is not None
        with self._registry.lease(generation_id) as generation:
            return build_exact_search_witness(
                generation,
                tuple(request.query_vector),
                top_k=request.top_k,
                metadata_filter=request.metadata_filter,
            )

    def close(self) -> None:
        """Release all resident generation handles and reject later warm reuse."""

        self._resource_cache.close()


def _text_sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


__all__ = [
    "IndexQueryChannel",
    "IndexQueryHit",
    "IndexQueryReport",
    "IndexQueryRequest",
    "IndexPreparationCacheStatus",
    "PreparedIndexGeneration",
    "IndexService",
]
