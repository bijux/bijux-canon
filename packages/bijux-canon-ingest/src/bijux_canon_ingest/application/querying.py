# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Query-time workflows for persisted indexes."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

from bijux_canon_ingest.retrieval.answering import ExtractiveAnswerer
from bijux_canon_ingest.retrieval.embedder_factory import embedder_for_model
from bijux_canon_ingest.retrieval.indexes import NumpyCosineIndex, load_index
from bijux_canon_ingest.retrieval.ports import Answer, Candidate, Embedder
from bijux_canon_ingest.retrieval.rerankers import LexicalOverlapReranker


def retrieve(
    *,
    index_path: Path,
    query: str,
    top_k: int = 5,
    filters: Mapping[str, str] | None = None,
    embedder: Embedder | None = None,
) -> list[Candidate]:
    """Retrieve ranked candidates from a persisted index."""

    idx = load_index(str(index_path))

    if isinstance(idx, NumpyCosineIndex) and embedder is None:
        embedder = embedder_for_model(idx.spec.model)

    return idx.retrieve(
        query=query, top_k=int(top_k), filters=filters, embedder=embedder
    )


def ask(
    *,
    index_path: Path,
    query: str,
    top_k: int = 5,
    filters: Mapping[str, str] | None = None,
    embedder: Embedder | None = None,
    rerank: bool = True,
) -> Answer:
    """Retrieve supporting chunks and generate an extractive answer."""

    candidates = retrieve(
        index_path=index_path,
        query=query,
        top_k=max(20, int(top_k)),
        filters=filters,
        embedder=embedder,
    )
    if rerank:
        candidates = LexicalOverlapReranker().rerank(
            query=query, candidates=candidates, top_k=int(top_k)
        )
    else:
        candidates = candidates[: int(top_k)]
    return ExtractiveAnswerer().generate(query=query, candidates=candidates)


def parse_filters(filters: list[str] | None) -> dict[str, str]:
    """Parse repeated ``key=value`` filters from the CLI or HTTP layer."""

    parsed: dict[str, str] = {}
    for raw_filter in filters or []:
        if "=" not in raw_filter:
            raise ValueError(f"invalid filter: {raw_filter}")
        key, value = raw_filter.split("=", 1)
        key = key.strip()
        value = value.strip()
        if not key or not value:
            raise ValueError(f"invalid filter: {raw_filter}")
        parsed[key] = value
    return parsed


__all__ = ["ask", "parse_filters", "retrieve"]
