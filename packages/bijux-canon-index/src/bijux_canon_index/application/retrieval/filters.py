# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Declared filter enforcement semantics for production retrieval channels."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_index.domain.metadata_filters import (
    GOVERNED_METADATA_FIELDS,
    MetadataOperator,
)


@dataclass(frozen=True, slots=True)
class RetrievalFilterCapability:
    """Inspectable filter behavior and limitations for one backend."""

    backend: str
    enforcement_stage: str
    governed_fields: tuple[str, ...]
    user_operators: tuple[str, ...]
    result_limit_applied_after_filter: bool
    limitations: tuple[str, ...]


_CAPABILITIES = {
    "sqlite-fts5": RetrievalFilterCapability(
        backend="sqlite-fts5",
        enforcement_stage="query_time_before_result_limit",
        governed_fields=GOVERNED_METADATA_FIELDS,
        user_operators=tuple(operator.value for operator in MetadataOperator),
        result_limit_applied_after_filter=True,
        limitations=(
            "typed range, collection, and caller-owned predicates are evaluated "
            "from canonical metadata rows after the FTS match",
        ),
    ),
    "faiss-flat-ip": RetrievalFilterCapability(
        backend="faiss-flat-ip",
        enforcement_stage="query_time_before_result_limit",
        governed_fields=GOVERNED_METADATA_FIELDS,
        user_operators=tuple(operator.value for operator in MetadataOperator),
        result_limit_applied_after_filter=True,
        limitations=(
            "filtered exact queries inspect admitted vector metadata in process",
        ),
    ),
    "faiss-hnsw": RetrievalFilterCapability(
        backend="faiss-hnsw",
        enforcement_stage="query_time_before_result_limit",
        governed_fields=GOVERNED_METADATA_FIELDS,
        user_operators=tuple(operator.value for operator in MetadataOperator),
        result_limit_applied_after_filter=True,
        limitations=(
            "filtered HNSW queries expand result inspection to the admitted "
            "generation size before applying the result limit",
        ),
    ),
}


def retrieval_filter_capability(backend: str) -> RetrievalFilterCapability:
    """Return filter semantics for a supported local retrieval backend."""

    try:
        return _CAPABILITIES[backend]
    except KeyError as error:
        raise ValueError("retrieval filter backend is unsupported") from error


__all__ = ["RetrievalFilterCapability", "retrieval_filter_capability"]
