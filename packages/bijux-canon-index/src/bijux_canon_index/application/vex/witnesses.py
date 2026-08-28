# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Content-bound exact-search witnesses for approximate retrieval."""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import date
from enum import Enum
import hashlib
import json
from typing import cast

from bijux_canon_index.application.index_generation import IndexGeneration
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.faiss.exact import (
    METRIC,
    NORMALIZATION,
    normalized_vector_sha256,
)


def _canonical_json(value: object) -> str:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


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


def _filter_payload(metadata_filter: MetadataFilter | None) -> dict[str, object]:
    if metadata_filter is None:
        return {}
    return cast(dict[str, object], _json_value(asdict(metadata_filter)))


@dataclass(frozen=True, slots=True)
class ExactSearchCandidate:
    """One exact ranked candidate without stored text or metadata values."""

    rank: int
    score: float
    chunk_id: str


@dataclass(frozen=True, slots=True)
class ExactSearchWitness:
    """Immutable exact ranking for one admitted approximation case."""

    schema_version: str
    witness_id: str
    generation_id: str
    model_lock_artifact_id: str
    backend: str
    backend_version: str
    metric: str
    normalization: str
    query_vector_sha256: str
    filter_sha256: str
    top_k: int
    candidates: tuple[ExactSearchCandidate, ...]
    candidate_order_sha256: str
    result_sha256: str


def build_exact_search_witness(
    generation: IndexGeneration,
    query_vector: tuple[float, ...],
    *,
    top_k: int,
    metadata_filter: MetadataFilter | None = None,
) -> ExactSearchWitness:
    """Record the exact reference for a dense query over one generation."""

    manifest = generation.manifest
    results = generation.exact.query(
        query_vector,
        top_k=top_k,
        metadata_filter=metadata_filter,
    )
    candidates = tuple(
        ExactSearchCandidate(
            rank=result.rank,
            score=result.score,
            chunk_id=result.chunk_id,
        )
        for result in results
    )
    candidate_payload = [asdict(candidate) for candidate in candidates]
    candidate_order_sha256 = _sha256_json(
        [candidate.chunk_id for candidate in candidates]
    )
    result_sha256 = _sha256_json(candidate_payload)
    identity = {
        "backend": "faiss-flat-ip",
        "backend_version": generation.exact.manifest.faiss_version,
        "candidate_order_sha256": candidate_order_sha256,
        "filter_sha256": _sha256_json(_filter_payload(metadata_filter)),
        "generation_id": manifest.generation_id,
        "metric": METRIC,
        "model_lock_artifact_id": manifest.model_lock_artifact_id,
        "normalization": NORMALIZATION,
        "query_vector_sha256": normalized_vector_sha256(
            query_vector,
            dimension=manifest.statistics.dimension,
        ),
        "result_sha256": result_sha256,
        "schema_version": "bijux.canon.vex.exact_witness.v1",
        "top_k": top_k,
    }
    return ExactSearchWitness(
        schema_version=str(identity["schema_version"]),
        witness_id=f"sha256:{_sha256_json(identity)}",
        generation_id=manifest.generation_id,
        model_lock_artifact_id=manifest.model_lock_artifact_id,
        backend="faiss-flat-ip",
        backend_version=generation.exact.manifest.faiss_version,
        metric=METRIC,
        normalization=NORMALIZATION,
        query_vector_sha256=str(identity["query_vector_sha256"]),
        filter_sha256=str(identity["filter_sha256"]),
        top_k=top_k,
        candidates=candidates,
        candidate_order_sha256=candidate_order_sha256,
        result_sha256=result_sha256,
    )


__all__ = [
    "ExactSearchCandidate",
    "ExactSearchWitness",
    "build_exact_search_witness",
]
