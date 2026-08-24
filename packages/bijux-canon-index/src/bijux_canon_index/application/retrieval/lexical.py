# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Generation-bound lexical candidate selection with auditable decisions."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum, StrEnum
import hashlib
import json
from pathlib import Path

from bijux_canon_index.application.index_activation import IndexGenerationRegistry
from bijux_canon_index.application.index_audit import IndexCompatibility
from bijux_canon_index.application.index_resource_cache import (
    IndexGenerationResourceCache,
)
from bijux_canon_index.contracts.authz import (
    RetrievalAuthorizationScope,
    authorize_retrieval_filter,
)
from bijux_canon_index.domain.metadata_filters import (
    MetadataFilter,
)
from bijux_canon_index.infra.adapters.sqlite.lexical import SQLiteLexicalIndex


class LexicalCandidateDisposition(StrEnum):
    """Why one BM25 match was retained or excluded."""

    included = "included"
    excluded_by_filter = "excluded_by_filter"
    excluded_by_limit = "excluded_by_limit"


class LexicalCandidateOutcome(StrEnum):
    """Typed result of one generation-bound lexical candidate request."""

    success = "success"
    empty_query = "empty_query"
    no_matches = "no_matches"
    filtered_empty = "filtered_empty"


@dataclass(frozen=True, slots=True)
class LexicalCandidateDecision:
    """One ranked BM25 match and its filter/limit disposition."""

    source_rank: int
    output_rank: int | None
    score: float
    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str
    disposition: LexicalCandidateDisposition


@dataclass(frozen=True, slots=True)
class LexicalCandidateBatch:
    """Complete lexical selection result bound to one admitted generation."""

    schema_version: str
    generation_id: str
    segment_generation_id: str
    tokenizer_configuration_sha256: str
    query_text_sha256: str
    filter_sha256: str
    requested_top_k: int
    candidate_limit: int
    outcome: LexicalCandidateOutcome
    decisions: tuple[LexicalCandidateDecision, ...]
    authorization_scope_id: str | None = None

    @property
    def candidates(self) -> tuple[LexicalCandidateDecision, ...]:
        """Return only admitted candidates in final rank order."""

        return tuple(
            decision
            for decision in self.decisions
            if decision.disposition is LexicalCandidateDisposition.included
        )


def _json_value(value: object) -> object:
    if isinstance(value, date):
        return value.isoformat()
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _sha256_json(value: object) -> str:
    raw = json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


class LexicalCandidateService:
    """Select lexical candidates only from a caller-selected admitted generation."""

    def __init__(
        self,
        registry_root: str | Path,
        *,
        compatibility: IndexCompatibility | None = None,
        resource_cache: IndexGenerationResourceCache | None = None,
    ) -> None:
        self._registry = IndexGenerationRegistry(
            registry_root,
            compatibility=compatibility,
            resource_cache=resource_cache,
        )

    def generate(
        self,
        query_text: str,
        *,
        generation_id: str,
        top_k: int,
        candidate_limit: int,
        metadata_filter: MetadataFilter | None = None,
        authorization_scope: RetrievalAuthorizationScope | None = None,
    ) -> LexicalCandidateBatch:
        """Generate bounded BM25 candidates with every selection decision."""

        if not 1 <= top_k <= 1000:
            raise ValueError("lexical top_k must be between 1 and 1000")
        if not top_k <= candidate_limit <= 1000:
            raise ValueError("lexical candidate_limit must be within [top_k,1000]")
        with self._registry.lease(generation_id) as generation:
            return self._generate(
                generation.lexical,
                query_text,
                generation_id=generation.manifest.generation_id,
                top_k=top_k,
                candidate_limit=candidate_limit,
                metadata_filter=metadata_filter,
                authorization_scope=authorization_scope,
            )

    def generate_from_segment(
        self,
        segment_path: str | Path,
        query_text: str,
        *,
        generation_id: str,
        top_k: int,
        candidate_limit: int,
        metadata_filter: MetadataFilter | None = None,
        authorization_scope: RetrievalAuthorizationScope | None = None,
    ) -> LexicalCandidateBatch:
        """Select candidates from one verified standalone lexical generation."""

        with SQLiteLexicalIndex(segment_path) as lexical:
            if lexical.manifest.generation_id != generation_id:
                raise ValueError("standalone lexical generation identity changed")
            return self._generate(
                lexical,
                query_text,
                generation_id=generation_id,
                top_k=top_k,
                candidate_limit=candidate_limit,
                metadata_filter=metadata_filter,
                authorization_scope=authorization_scope,
            )

    @staticmethod
    def _generate(
        lexical: SQLiteLexicalIndex,
        query_text: str,
        *,
        generation_id: str,
        top_k: int,
        candidate_limit: int,
        metadata_filter: MetadataFilter | None,
        authorization_scope: RetrievalAuthorizationScope | None,
    ) -> LexicalCandidateBatch:
        if not 1 <= top_k <= 1000:
            raise ValueError("lexical top_k must be between 1 and 1000")
        if not top_k <= candidate_limit <= 1000:
            raise ValueError("lexical candidate_limit must be within [top_k,1000]")
        effective_filter = authorize_retrieval_filter(
            authorization_scope,
            generation_id=generation_id,
            requested=metadata_filter,
        )
        query_sha256 = hashlib.sha256(query_text.encode("utf-8")).hexdigest()
        filter_sha256 = _sha256_json(
            {} if effective_filter is None else asdict(effective_filter)
        )
        authorization_scope_id = (
            None if authorization_scope is None else authorization_scope.artifact_id
        )
        manifest = lexical.manifest
        if not query_text.strip():
            return LexicalCandidateBatch(
                schema_version="bijux.canon.retrieval.lexical_candidates.v1",
                generation_id=generation_id,
                segment_generation_id=manifest.generation_id,
                tokenizer_configuration_sha256=(
                    manifest.tokenizer_configuration_sha256
                ),
                query_text_sha256=query_sha256,
                filter_sha256=filter_sha256,
                requested_top_k=top_k,
                candidate_limit=candidate_limit,
                outcome=LexicalCandidateOutcome.empty_query,
                decisions=(),
                authorization_scope_id=authorization_scope_id,
            )
        matches = lexical.query(
            query_text,
            top_k=candidate_limit,
            metadata_filter=effective_filter,
        )
        decisions = []
        output_rank = 0
        for match in matches:
            if output_rank == top_k:
                disposition = LexicalCandidateDisposition.excluded_by_limit
                selected_rank = None
            else:
                output_rank += 1
                disposition = LexicalCandidateDisposition.included
                selected_rank = output_rank
            decisions.append(
                LexicalCandidateDecision(
                    source_rank=match.rank,
                    output_rank=selected_rank,
                    score=match.score,
                    chunk_id=match.chunk.chunk_id,
                    document_id=match.chunk.document_id,
                    ordinal=match.chunk.ordinal,
                    source_text_sha256=hashlib.sha256(
                        match.chunk.text.encode("utf-8")
                    ).hexdigest(),
                    disposition=disposition,
                )
            )
        if output_rank:
            outcome = LexicalCandidateOutcome.success
        elif effective_filter is not None:
            unfiltered_probe = lexical.query(query_text, top_k=1)
            outcome = (
                LexicalCandidateOutcome.filtered_empty
                if unfiltered_probe
                else LexicalCandidateOutcome.no_matches
            )
        else:
            outcome = LexicalCandidateOutcome.no_matches
        return LexicalCandidateBatch(
            schema_version="bijux.canon.retrieval.lexical_candidates.v1",
            generation_id=generation_id,
            segment_generation_id=manifest.generation_id,
            tokenizer_configuration_sha256=(manifest.tokenizer_configuration_sha256),
            query_text_sha256=query_sha256,
            filter_sha256=filter_sha256,
            requested_top_k=top_k,
            candidate_limit=candidate_limit,
            outcome=outcome,
            decisions=tuple(decisions),
            authorization_scope_id=authorization_scope_id,
        )


__all__ = [
    "LexicalCandidateBatch",
    "LexicalCandidateDecision",
    "LexicalCandidateDisposition",
    "LexicalCandidateOutcome",
    "LexicalCandidateService",
]
