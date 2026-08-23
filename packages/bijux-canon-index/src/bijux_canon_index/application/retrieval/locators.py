# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Resolve retrieval candidates to exact ingest-owned citation locators."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from enum import Enum, StrEnum
import hashlib
import json
import math
from pathlib import Path

from bijux_canon_index.application.index_activation import IndexGenerationRegistry
from bijux_canon_index.application.index_audit import IndexCompatibility

from .dense import DenseCandidateBatch, DenseCandidateMode, DenseCandidateOutcome
from .fusion import RetrievalChannel, RrfFusionBatch
from .lexical import LexicalCandidateBatch, LexicalCandidateOutcome
from .reranking import RerankBatch, RerankOutcome

LocatorValue = str | int


class CitationRetrievalMode(StrEnum):
    """Retrieval profiles whose channel lineage is preserved in citations."""

    lexical = "lexical"
    dense_exact = "dense-exact"
    local_hybrid_exact = "local-hybrid-exact"
    local_hybrid_ann = "local-hybrid-ann"


class CitationChannel(StrEnum):
    """Concrete candidate-producing channels, including dense execution mode."""

    lexical = "lexical"
    dense_exact = "dense-exact"
    dense_ann = "dense-ann"


class CitationResolutionErrorCode(StrEnum):
    """Stable refusal reasons for missing or contradictory citation truth."""

    candidate_set_invalid = "candidate_set_invalid"
    catalog_invalid = "catalog_invalid"
    generation_mismatch = "generation_mismatch"
    locator_ambiguous = "locator_ambiguous"
    locator_missing = "locator_missing"
    source_identity_mismatch = "source_identity_mismatch"
    text_identity_mismatch = "text_identity_mismatch"


class CitationResolutionError(ValueError):
    """A candidate cannot be resolved to exactly one immutable source locator."""

    def __init__(self, code: CitationResolutionErrorCode, message: str) -> None:
        super().__init__(message)
        self.code = code


def _is_sha256(value: str) -> bool:
    return len(value) == 64 and all(
        character in "0123456789abcdef" for character in value
    )


def _is_artifact_id(value: str) -> bool:
    return value.startswith("sha256:") and _is_sha256(value.removeprefix("sha256:"))


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _sha256_json(value: object) -> str:
    encoded = json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _artifact_id(value: object) -> str:
    return f"sha256:{_sha256_json(value)}"


@dataclass(frozen=True, slots=True)
class CitationSourceMetadata:
    """Bibliographic and content identity supplied by the ingest owner."""

    source_id: str
    source_uri: str
    source_content_sha256: str
    format_id: str
    title: str
    authors: tuple[str, ...] = ()
    doi: str | None = None
    language: str | None = None
    license_id: str | None = None

    def __post_init__(self) -> None:
        if not all((self.source_id, self.source_uri, self.format_id, self.title)):
            raise ValueError("citation source metadata requires stable source fields")
        if not _is_sha256(self.source_content_sha256):
            raise ValueError("citation source content identity must be a SHA-256")
        if any(not author for author in self.authors):
            raise ValueError("citation source authors must not be empty")


@dataclass(frozen=True, slots=True)
class ExactSourceLocator:
    """Ingest-owned locator scheme with typed source selectors."""

    scheme: str
    selectors: tuple[tuple[str, LocatorValue], ...]

    def __post_init__(self) -> None:
        names = tuple(name for name, _ in self.selectors)
        if (
            not self.scheme
            or not names
            or any(not name for name in names)
            or len(names) != len(set(names))
        ):
            raise ValueError("exact source locator requires unique named selectors")
        selector_map = dict(self.selectors)
        has_span = any(
            start in selector_map and end in selector_map
            for start, end in (
                ("char_start", "char_end"),
                ("text_start", "text_end"),
                ("byte_start", "byte_end"),
            )
        )
        structural = {
            "block_index",
            "dom_path",
            "element_path",
            "line_start",
            "page_number",
            "paragraph_number",
            "window_ordinal",
        }
        if not has_span and not structural.intersection(selector_map):
            raise ValueError(
                "exact source locator requires a page, paragraph, structure, or span"
            )
        for start, end in (
            ("char_start", "char_end"),
            ("text_start", "text_end"),
            ("byte_start", "byte_end"),
        ):
            if start in selector_map or end in selector_map:
                if not isinstance(selector_map.get(start), int) or not isinstance(
                    selector_map.get(end), int
                ):
                    raise ValueError("source locator span coordinates must be integers")
                if int(selector_map[start]) < 0 or int(selector_map[end]) <= int(
                    selector_map[start]
                ):
                    raise ValueError(
                        "source locator span must be non-empty and ordered"
                    )


@dataclass(frozen=True, slots=True)
class CitationLocatorSegment:
    """One exact chunk span resolved by one ingest format locator."""

    ordinal: int
    mapping_id: str
    chunk_start: int
    chunk_end: int
    normalized_start: int
    normalized_end: int
    section_path: tuple[str, ...]
    locator: ExactSourceLocator
    verbatim_text: str
    content_sha256: str

    def __post_init__(self) -> None:
        if (
            self.ordinal < 0
            or not _is_artifact_id(self.mapping_id)
            or self.chunk_start < 0
            or self.chunk_end <= self.chunk_start
            or self.normalized_start < 0
            or self.normalized_end <= self.normalized_start
            or self.chunk_end - self.chunk_start != len(self.verbatim_text)
            or self.normalized_end - self.normalized_start != len(self.verbatim_text)
            or not self.verbatim_text
            or not self.section_path
            or any(not item for item in self.section_path)
        ):
            raise ValueError("citation locator segment coordinates are invalid")
        if hashlib.sha256(self.verbatim_text.encode()).hexdigest() != (
            self.content_sha256
        ):
            raise ValueError("citation locator segment text identity does not match")

    @property
    def segment_id(self) -> str:
        """Return the complete segment content identity."""

        return _artifact_id(asdict(self))


@dataclass(frozen=True, slots=True)
class CitationLocatorRecord:
    """Exact citation truth for one immutable chunk, supplied by ingest."""

    chunk_id: str
    document_id: str
    ordinal: int
    source: CitationSourceMetadata
    section_path: tuple[str, ...]
    locator: ExactSourceLocator
    verbatim_text: str
    content_sha256: str
    mapping_ids: tuple[str, ...]
    parent_chunk_ids: tuple[str, ...] = ()
    locator_segments: tuple[CitationLocatorSegment, ...] = ()
    locator_scope: str = field(init=False)

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.document_id or self.ordinal < 0:
            raise ValueError("citation locator requires a chunk identity and ordinal")
        if not self.section_path or any(not item for item in self.section_path):
            raise ValueError("citation locator requires a non-empty section path")
        if not self.verbatim_text:
            raise ValueError("citation locator verbatim text must not be empty")
        if hashlib.sha256(self.verbatim_text.encode("utf-8")).hexdigest() != (
            self.content_sha256
        ):
            raise ValueError("citation locator content hash does not match its text")
        if (
            not self.mapping_ids
            or len(self.mapping_ids) != len(set(self.mapping_ids))
            or any(not _is_artifact_id(item) for item in self.mapping_ids)
        ):
            raise ValueError("citation locator requires unique mapping identities")
        if len(self.parent_chunk_ids) != len(set(self.parent_chunk_ids)) or any(
            not item for item in self.parent_chunk_ids
        ):
            raise ValueError("citation parent chunk identities must be unique")
        if not self.locator_segments:
            object.__setattr__(
                self,
                "locator_segments",
                (
                    CitationLocatorSegment(
                        ordinal=0,
                        mapping_id=self.mapping_ids[0],
                        chunk_start=0,
                        chunk_end=len(self.verbatim_text),
                        normalized_start=0,
                        normalized_end=len(self.verbatim_text),
                        section_path=self.section_path,
                        locator=self.locator,
                        verbatim_text=self.verbatim_text,
                        content_sha256=self.content_sha256,
                    ),
                ),
            )
        if tuple(segment.ordinal for segment in self.locator_segments) != tuple(
            range(len(self.locator_segments))
        ) or any(
            left.chunk_end > right.chunk_start
            for left, right in zip(
                self.locator_segments,
                self.locator_segments[1:],
                strict=False,
            )
        ):
            raise ValueError("citation locator segments must be ordered and disjoint")
        if tuple(segment.mapping_id for segment in self.locator_segments) != (
            self.mapping_ids
        ) or any(
            self.verbatim_text[segment.chunk_start : segment.chunk_end]
            != segment.verbatim_text
            for segment in self.locator_segments
        ):
            raise ValueError("citation locator segments do not resolve record text")
        if self.locator != self.locator_segments[0].locator:
            raise ValueError("citation primary locator must be the first exact segment")
        object.__setattr__(
            self,
            "locator_scope",
            (
                "complete-chunk"
                if len(self.locator_segments) == 1
                else "first-segment-only"
            ),
        )

    @property
    def locator_record_id(self) -> str:
        """Return the complete locator-record content identity."""

        return _artifact_id(asdict(self))


@dataclass(frozen=True, slots=True)
class CitationLocatorCatalog:
    """Snapshot-bound ingest output used to resolve index candidates."""

    schema_version: str
    snapshot_artifact_id: str
    records: tuple[CitationLocatorRecord, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.canon.ingest.citation_locator_catalog.v1":
            raise ValueError("citation locator catalog schema is unsupported")
        if not self.snapshot_artifact_id or not self.records:
            raise ValueError("citation locator catalog requires a snapshot and records")

    @property
    def catalog_id(self) -> str:
        """Return the immutable catalog identity independent of input order."""

        records = sorted(
            (asdict(record) for record in self.records),
            key=lambda record: str(record["chunk_id"]),
        )
        return _artifact_id(
            {
                "records": records,
                "schema_version": self.schema_version,
                "snapshot_artifact_id": self.snapshot_artifact_id,
            }
        )


@dataclass(frozen=True, slots=True)
class CitationChannelProvenance:
    """Rank, score, and artifact identity contributed by one retrieval channel."""

    channel: CitationChannel
    rank: int
    score: float
    candidate_artifact_id: str
    execution_artifact_id: str | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.channel, CitationChannel) or self.rank <= 0:
            raise ValueError("citation channel provenance is invalid")
        if not math.isfinite(self.score):
            raise ValueError("citation channel score must be finite")
        if not _is_artifact_id(self.candidate_artifact_id):
            raise ValueError("citation candidate artifact identity is invalid")
        if self.execution_artifact_id is not None and not _is_artifact_id(
            self.execution_artifact_id
        ):
            raise ValueError("citation execution artifact identity is invalid")


@dataclass(frozen=True, slots=True)
class CitationCandidate:
    """A retrieval result normalized for exact locator resolution."""

    rank: int
    retrieval_rank: int
    retrieval_score: float
    rerank_score: float | None
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str
    channels: tuple[CitationChannelProvenance, ...]

    def __post_init__(self) -> None:
        if self.rank <= 0 or self.retrieval_rank <= 0 or self.ordinal < 0:
            raise ValueError("citation candidate ranks and ordinal are invalid")
        if not self.chunk_id or not self.document_id:
            raise ValueError("citation candidate identities must not be empty")
        if not math.isfinite(self.retrieval_score) or (
            self.rerank_score is not None and not math.isfinite(self.rerank_score)
        ):
            raise ValueError("citation candidate scores must be finite")
        if not _is_sha256(self.source_text_sha256):
            raise ValueError("citation candidate text identity must be a SHA-256")
        channel_names = tuple(channel.channel for channel in self.channels)
        if not channel_names or len(channel_names) != len(set(channel_names)):
            raise ValueError("citation candidate channels must be unique and non-empty")


@dataclass(frozen=True, slots=True)
class CitationReadyHit:
    """A ranked hit carrying source metadata, exact text, and complete lineage."""

    artifact_id: str
    rank: int
    retrieval_rank: int
    retrieval_score: float
    rerank_score: float | None
    chunk_id: str
    document_id: str
    ordinal: int
    source: CitationSourceMetadata
    section_path: tuple[str, ...]
    locator: ExactSourceLocator
    locator_scope: str
    locator_segments: tuple[CitationLocatorSegment, ...]
    verbatim_text: str
    content_sha256: str
    mapping_ids: tuple[str, ...]
    parent_chunk_ids: tuple[str, ...]
    locator_record_id: str
    channels: tuple[CitationChannelProvenance, ...]


@dataclass(frozen=True, slots=True)
class CitationResolutionBatch:
    """Generation- and snapshot-bound citation-ready retrieval result."""

    schema_version: str
    generation_id: str
    snapshot_artifact_id: str
    query_text_sha256: str
    retrieval_mode: CitationRetrievalMode
    locator_catalog_id: str
    hits: tuple[CitationReadyHit, ...]


def _direct_candidate_id(
    *,
    channel: CitationChannel,
    generation_id: str,
    query_text_sha256: str,
    rank: int,
    score: float,
    chunk_id: str,
) -> str:
    return _artifact_id(
        {
            "channel": channel.value,
            "chunk_id": chunk_id,
            "generation_id": generation_id,
            "query_text_sha256": query_text_sha256,
            "rank": rank,
            "score": score,
        }
    )


def citation_candidates_from_lexical(
    batch: LexicalCandidateBatch,
) -> tuple[CitationCandidate, ...]:
    """Normalize one admitted lexical batch without losing BM25 provenance."""

    if batch.outcome is LexicalCandidateOutcome.empty_query:
        raise ValueError("empty lexical queries cannot resolve citations")
    result = []
    for item in batch.candidates:
        assert item.output_rank is not None
        candidate_id = _direct_candidate_id(
            channel=CitationChannel.lexical,
            generation_id=batch.generation_id,
            query_text_sha256=batch.query_text_sha256,
            rank=item.source_rank,
            score=item.score,
            chunk_id=item.chunk_id,
        )
        result.append(
            CitationCandidate(
                rank=item.output_rank,
                retrieval_rank=item.output_rank,
                retrieval_score=item.score,
                rerank_score=None,
                chunk_id=item.chunk_id,
                document_id=item.document_id,
                ordinal=item.ordinal,
                source_text_sha256=item.source_text_sha256,
                channels=(
                    CitationChannelProvenance(
                        CitationChannel.lexical,
                        item.source_rank,
                        item.score,
                        candidate_id,
                    ),
                ),
            )
        )
    return tuple(result)


def citation_candidates_from_dense(
    batch: DenseCandidateBatch,
) -> tuple[CitationCandidate, ...]:
    """Normalize one policy-admitted VEX batch with its execution identity."""

    if batch.outcome is DenseCandidateOutcome.refused:
        raise ValueError("refused dense executions cannot resolve citations")
    channel = (
        CitationChannel.dense_exact
        if batch.mode is DenseCandidateMode.exact
        else CitationChannel.dense_ann
    )
    return tuple(
        CitationCandidate(
            rank=item.source_rank,
            retrieval_rank=item.source_rank,
            retrieval_score=item.score,
            rerank_score=None,
            chunk_id=item.chunk_id,
            document_id=item.document_id,
            ordinal=item.ordinal,
            source_text_sha256=item.source_text_sha256,
            channels=(
                CitationChannelProvenance(
                    channel,
                    item.source_rank,
                    item.score,
                    _direct_candidate_id(
                        channel=channel,
                        generation_id=batch.generation_id,
                        query_text_sha256=batch.query_text_sha256,
                        rank=item.source_rank,
                        score=item.score,
                        chunk_id=item.chunk_id,
                    ),
                    batch.artifact_id,
                ),
            ),
        )
        for item in batch.candidates[: batch.requested_top_k]
    )


def _fused_channels(
    fusion: RrfFusionBatch,
    *,
    dense_mode: DenseCandidateMode,
) -> tuple[tuple[CitationChannelProvenance, ...], ...]:
    dense_channel = (
        CitationChannel.dense_exact
        if dense_mode is DenseCandidateMode.exact
        else CitationChannel.dense_ann
    )
    result = []
    for hit in fusion.hits:
        channels = tuple(
            CitationChannelProvenance(
                CitationChannel.lexical
                if contribution.channel is RetrievalChannel.lexical
                else dense_channel,
                contribution.channel_rank,
                contribution.channel_score,
                contribution.candidate_artifact_id,
            )
            for contribution in hit.contributions
        )
        result.append(channels)
    return tuple(result)


def citation_candidates_from_fusion(
    fusion: RrfFusionBatch,
    *,
    dense_mode: DenseCandidateMode,
) -> tuple[CitationCandidate, ...]:
    """Normalize hybrid hits while retaining every weighted-RRF contribution."""

    channel_sets = _fused_channels(fusion, dense_mode=dense_mode)
    return tuple(
        CitationCandidate(
            rank=hit.rank,
            retrieval_rank=hit.rank,
            retrieval_score=hit.fused_score,
            rerank_score=None,
            chunk_id=hit.chunk_id,
            document_id=hit.document_id,
            ordinal=hit.ordinal,
            source_text_sha256=hit.source_text_sha256,
            channels=channels,
        )
        for hit, channels in zip(fusion.hits, channel_sets, strict=True)
    )


def citation_candidates_from_rerank(
    batch: RerankBatch,
    *,
    dense_mode: DenseCandidateMode,
) -> tuple[CitationCandidate, ...]:
    """Normalize final reranked hits without replacing retrieval truth."""

    if batch.outcome is RerankOutcome.refused:
        raise ValueError("refused reranking cannot resolve citations")
    dense_channel = (
        CitationChannel.dense_exact
        if dense_mode is DenseCandidateMode.exact
        else CitationChannel.dense_ann
    )
    result = []
    for item in batch.candidates:
        channels = tuple(
            CitationChannelProvenance(
                CitationChannel.lexical
                if contribution.channel is RetrievalChannel.lexical
                else dense_channel,
                contribution.channel_rank,
                contribution.channel_score,
                contribution.candidate_artifact_id,
            )
            for contribution in item.candidate.contributions
        )
        result.append(
            CitationCandidate(
                rank=item.rank,
                retrieval_rank=item.retrieval_rank,
                retrieval_score=item.fused_score,
                rerank_score=item.rerank_score,
                chunk_id=item.chunk_id,
                document_id=item.candidate.document_id,
                ordinal=item.candidate.ordinal,
                source_text_sha256=item.candidate.source_text_sha256,
                channels=channels,
            )
        )
    return tuple(result)


def _allowed_channels(mode: CitationRetrievalMode) -> frozenset[CitationChannel]:
    if mode is CitationRetrievalMode.lexical:
        return frozenset({CitationChannel.lexical})
    if mode is CitationRetrievalMode.dense_exact:
        return frozenset({CitationChannel.dense_exact})
    if mode is CitationRetrievalMode.local_hybrid_exact:
        return frozenset({CitationChannel.lexical, CitationChannel.dense_exact})
    return frozenset({CitationChannel.lexical, CitationChannel.dense_ann})


class CitationLocatorService:
    """Attach exact ingest-owned citation truth to verified index candidates."""

    def __init__(
        self,
        registry_root: str | Path,
        *,
        compatibility: IndexCompatibility | None = None,
    ) -> None:
        self._registry = IndexGenerationRegistry(
            registry_root,
            compatibility=compatibility,
        )

    def resolve(
        self,
        candidates: tuple[CitationCandidate, ...],
        *,
        generation_id: str,
        query_text_sha256: str,
        retrieval_mode: CitationRetrievalMode,
        catalog: CitationLocatorCatalog,
    ) -> CitationResolutionBatch:
        """Resolve every candidate exactly once or refuse the whole result."""

        if not _is_sha256(query_text_sha256):
            raise CitationResolutionError(
                CitationResolutionErrorCode.candidate_set_invalid,
                "citation query identity must be a SHA-256",
            )
        if not isinstance(retrieval_mode, CitationRetrievalMode):
            raise CitationResolutionError(
                CitationResolutionErrorCode.candidate_set_invalid,
                "citation retrieval mode is unsupported",
            )
        ranks = tuple(candidate.rank for candidate in candidates)
        chunk_ids = tuple(candidate.chunk_id for candidate in candidates)
        if ranks != tuple(range(1, len(candidates) + 1)) or len(chunk_ids) != len(
            set(chunk_ids)
        ):
            raise CitationResolutionError(
                CitationResolutionErrorCode.candidate_set_invalid,
                "citation candidates must have contiguous ranks and unique chunks",
            )
        allowed = _allowed_channels(retrieval_mode)
        if any(
            not {channel.channel for channel in candidate.channels}.issubset(allowed)
            for candidate in candidates
        ):
            raise CitationResolutionError(
                CitationResolutionErrorCode.candidate_set_invalid,
                "citation channel provenance does not match retrieval mode",
            )

        records_by_chunk: dict[str, CitationLocatorRecord] = {}
        duplicate_ids: set[str] = set()
        for catalog_record in catalog.records:
            if catalog_record.chunk_id in records_by_chunk:
                duplicate_ids.add(catalog_record.chunk_id)
            records_by_chunk[catalog_record.chunk_id] = catalog_record
        if duplicate_ids:
            raise CitationResolutionError(
                CitationResolutionErrorCode.locator_ambiguous,
                "citation locator catalog contains duplicate chunk mappings",
            )

        with self._registry.open(generation_id) as generation:
            manifest = generation.manifest
            if manifest.generation_id != generation_id:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.generation_mismatch,
                    "opened index generation identity changed",
                )
            if manifest.snapshot_artifact_id != catalog.snapshot_artifact_id:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.generation_mismatch,
                    "locator catalog snapshot does not match index generation",
                )
            admitted = {chunk.chunk_id: chunk for chunk in generation.admitted_chunks()}

        hits = []
        for candidate in candidates:
            chunk = admitted.get(candidate.chunk_id)
            if chunk is None:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.generation_mismatch,
                    "retrieval candidate is not admitted by the selected generation",
                )
            record = records_by_chunk.get(candidate.chunk_id)
            if record is None:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.locator_missing,
                    "retrieval candidate has no ingest-owned locator mapping",
                )
            text_sha256 = hashlib.sha256(chunk.text.encode("utf-8")).hexdigest()
            immutable_candidate = (
                candidate.document_id,
                candidate.ordinal,
                candidate.source_text_sha256,
            )
            immutable_chunk = (chunk.document_id, chunk.ordinal, text_sha256)
            immutable_record = (
                record.document_id,
                record.ordinal,
                record.content_sha256,
            )
            if immutable_candidate != immutable_chunk or immutable_record != (
                chunk.document_id,
                chunk.ordinal,
                text_sha256,
            ):
                raise CitationResolutionError(
                    CitationResolutionErrorCode.text_identity_mismatch,
                    "candidate, index chunk, and locator text identities disagree",
                )
            if record.verbatim_text != chunk.text:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.text_identity_mismatch,
                    "locator verbatim text differs from the admitted index chunk",
                )
            metadata = dict(chunk.metadata)
            if metadata.get("source_id") != record.source.source_id:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.source_identity_mismatch,
                    "locator source identity differs from index metadata",
                )
            if metadata.get("source_sha256") != record.source.source_content_sha256:
                raise CitationResolutionError(
                    CitationResolutionErrorCode.source_identity_mismatch,
                    "locator source hash differs from index metadata",
                )
            optional_metadata = {
                "doi": record.source.doi,
                "format": record.source.format_id,
                "language": record.source.language,
            }
            if any(
                key in metadata and expected is not None and metadata[key] != expected
                for key, expected in optional_metadata.items()
            ):
                raise CitationResolutionError(
                    CitationResolutionErrorCode.source_identity_mismatch,
                    "locator bibliographic metadata differs from index metadata",
                )
            hit_payload = {
                "candidate": asdict(candidate),
                "generation_id": generation_id,
                "locator_record_id": record.locator_record_id,
                "query_text_sha256": query_text_sha256,
                "retrieval_mode": retrieval_mode,
            }
            hits.append(
                CitationReadyHit(
                    artifact_id=_artifact_id(hit_payload),
                    rank=candidate.rank,
                    retrieval_rank=candidate.retrieval_rank,
                    retrieval_score=candidate.retrieval_score,
                    rerank_score=candidate.rerank_score,
                    chunk_id=candidate.chunk_id,
                    document_id=candidate.document_id,
                    ordinal=candidate.ordinal,
                    source=record.source,
                    section_path=record.section_path,
                    locator=record.locator,
                    locator_scope=record.locator_scope,
                    locator_segments=record.locator_segments,
                    verbatim_text=record.verbatim_text,
                    content_sha256=record.content_sha256,
                    mapping_ids=record.mapping_ids,
                    parent_chunk_ids=record.parent_chunk_ids,
                    locator_record_id=record.locator_record_id,
                    channels=candidate.channels,
                )
            )
        return CitationResolutionBatch(
            schema_version="bijux.canon.retrieval.citation_resolution.v1",
            generation_id=generation_id,
            snapshot_artifact_id=catalog.snapshot_artifact_id,
            query_text_sha256=query_text_sha256,
            retrieval_mode=retrieval_mode,
            locator_catalog_id=catalog.catalog_id,
            hits=tuple(hits),
        )


__all__ = [
    "CitationCandidate",
    "CitationChannel",
    "CitationChannelProvenance",
    "CitationLocatorCatalog",
    "CitationLocatorRecord",
    "CitationLocatorSegment",
    "CitationLocatorService",
    "CitationReadyHit",
    "CitationResolutionBatch",
    "CitationResolutionError",
    "CitationResolutionErrorCode",
    "CitationRetrievalMode",
    "CitationSourceMetadata",
    "ExactSourceLocator",
    "LocatorValue",
    "citation_candidates_from_dense",
    "citation_candidates_from_fusion",
    "citation_candidates_from_lexical",
    "citation_candidates_from_rerank",
]
