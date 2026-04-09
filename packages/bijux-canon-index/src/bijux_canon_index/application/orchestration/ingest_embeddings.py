# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Ingest embeddings helpers for application workflows."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_index.core.config import ExecutionConfig
from bijux_canon_index.core.errors import ValidationError
from bijux_canon_index.infra.embeddings.cache import (
    EmbeddingCacheEntry,
    build_cache,
    cache_key,
    embedding_config_hash,
    metadata_as_dict,
)
from bijux_canon_index.infra.embeddings.registry import EMBEDDING_PROVIDERS
from bijux_canon_index.interfaces.schemas.requests import IngestRequest


@dataclass(frozen=True)
class PreparedIngestVectors:
    """Represents prepared ingest vectors."""
    vectors: list[list[float]]
    embedding_meta_by_index: dict[int, dict[str, str | None]]
    embedding_model: str | None


def prepare_ingest_vectors(
    req: IngestRequest, config: ExecutionConfig
) -> PreparedIngestVectors:
    """Handle prepare ingest vectors."""
    vectors_input = list(req.vectors or [])
    if vectors_input:
        return PreparedIngestVectors(
            vectors=vectors_input,
            embedding_meta_by_index={},
            embedding_model=None,
        )
    embed_provider = None
    embed_model = None
    cache_spec = None
    if config.embeddings is not None:
        embed_provider = config.embeddings.provider
        embed_model = config.embeddings.model
        if config.embeddings.cache is not None:
            cache_spec = config.embeddings.cache.uri or config.embeddings.cache.backend
    embed_provider = embed_provider or req.embed_provider
    embed_model = embed_model or req.embed_model
    cache_spec = cache_spec or req.cache_embeddings
    if not embed_model:
        raise ValidationError(message="embed_model required when vectors are omitted")
    try:
        provider = EMBEDDING_PROVIDERS.resolve(embed_provider)
    except ValueError as exc:
        raise ValidationError(message=str(exc)) from exc
    options: dict[str, str] = {"normalize": "false"}
    config_hash = embedding_config_hash(
        provider.name,
        embed_model,
        options,
        provider_version=provider.provider_version,
    )
    try:
        cache = build_cache(cache_spec)
    except ValueError as exc:
        raise ValidationError(message=str(exc)) from exc
    pending_texts: list[str] = []
    pending_idx: list[int] = []
    vectors = [[0.0] for _ in req.documents]
    embedding_meta_by_index: dict[int, dict[str, str | None]] = {}
    if cache is not None:
        for idx, doc_text in enumerate(req.documents):
            key = cache_key(embed_model, doc_text, config_hash)
            entry = cache.get(key)
            if entry:
                expected = {
                    "embedding_provider": provider.name,
                    "embedding_provider_version": provider.provider_version,
                    "embedding_normalization": options.get("normalize"),
                }
                if any(
                    entry.metadata.get(k) != ("" if v is None else str(v))
                    for k, v in expected.items()
                ):
                    entry = None
            if entry:
                vectors[idx] = list(entry.vector)
                embedding_meta_by_index[idx] = entry.metadata
            else:
                pending_texts.append(doc_text)
                pending_idx.append(idx)
    else:
        pending_texts = list(req.documents)
        pending_idx = list(range(len(req.documents)))
    if pending_texts:
        batch = provider.embed(pending_texts, embed_model, options=options)
        if len(batch.vectors) != len(pending_idx):
            raise ValidationError(
                message="embedding provider returned mismatched vector count"
            )
        if not batch.metadata.embedding_determinism:
            raise ValidationError(
                message="embedding provider did not declare determinism"
            )
        for idx, embed_vec in zip(pending_idx, batch.vectors, strict=False):
            vectors[idx] = list(embed_vec)
            meta_dict = metadata_as_dict(
                {
                    "embedding_provider": batch.metadata.provider,
                    "embedding_provider_version": batch.metadata.provider_version,
                    "embedding_model_version": batch.metadata.model_version,
                    "embedding_determinism": batch.metadata.embedding_determinism,
                    "embedding_seed": batch.metadata.embedding_seed,
                    "embedding_device": batch.metadata.embedding_device,
                    "embedding_dtype": batch.metadata.embedding_dtype,
                    "embedding_normalization": batch.metadata.embedding_normalization,
                }
            )
            embedding_meta_by_index[idx] = meta_dict
            if cache is not None:
                key = cache_key(
                    batch.metadata.model,
                    req.documents[idx],
                    batch.metadata.config_hash,
                )
                cache.set(
                    key,
                    entry=EmbeddingCacheEntry(
                        vector=tuple(embed_vec),
                        metadata=meta_dict,
                    ),
                )
    return PreparedIngestVectors(
        vectors=vectors,
        embedding_meta_by_index=embedding_meta_by_index,
        embedding_model=embed_model,
    )


__all__ = ["PreparedIngestVectors", "prepare_ingest_vectors"]
