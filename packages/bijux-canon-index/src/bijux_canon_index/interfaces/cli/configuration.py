# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Configuration and enum parsing helpers for the CLI boundary."""

from __future__ import annotations

from pathlib import Path

import typer

from bijux_canon_index.core.config import (
    EmbeddingCacheConfig,
    EmbeddingConfig,
    ExecutionConfig,
    ResourceLimits,
    VectorStoreConfig,
)
from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.execution_intent import ExecutionIntent
from bijux_canon_index.core.execution_mode import ExecutionMode

ALLOWED_INTENTS = {intent.value for intent in ExecutionIntent}


def parse_contract(raw: str) -> ExecutionContract:
    try:
        return ExecutionContract(raw)
    except Exception:
        typer.echo("execution-contract must be one of deterministic|non_deterministic")
        raise typer.Exit(code=1) from None


def parse_mode(raw: str) -> ExecutionMode:
    try:
        return ExecutionMode(raw)
    except Exception:
        typer.echo("execution-mode must be one of strict|bounded|exploratory")
        raise typer.Exit(code=1) from None


def parse_intent(raw: str) -> ExecutionIntent:
    if raw not in ALLOWED_INTENTS:
        allowed = "|".join(sorted(ALLOWED_INTENTS))
        typer.echo(f"execution-intent must be one of {allowed}")
        raise typer.Exit(code=1)
    return ExecutionIntent(raw)


def load_config(config_path: Path | None) -> ExecutionConfig | None:
    if not config_path:
        return None

    suffix = config_path.suffix.lower()
    if suffix in {".toml", ".tml"}:
        import tomllib

        payload = tomllib.loads(config_path.read_text(encoding="utf-8"))
    elif suffix in {".yaml", ".yml"}:
        try:
            import yaml
        except Exception as exc:  # pragma: no cover
            raise ValueError(
                "YAML config requires PyYAML. Install with extras or use TOML."
            ) from exc
        payload = yaml.safe_load(config_path.read_text(encoding="utf-8")) or {}
    else:
        raise ValueError("config file must be .toml or .yaml/.yml")

    vector_store_cfg = payload.get("vector_store") or {}
    embedding_cfg = payload.get("embeddings") or {}
    limits_cfg = payload.get("resource_limits") or {}
    cache_cfg = embedding_cfg.get("cache") or {}

    vector_store = None
    if vector_store_cfg.get("backend"):
        vector_store = VectorStoreConfig(
            backend=vector_store_cfg.get("backend"),
            uri=vector_store_cfg.get("uri"),
        )

    embeddings = None
    if embedding_cfg.get("provider") or embedding_cfg.get("model") or cache_cfg.get("uri"):
        embeddings = EmbeddingConfig(
            provider=embedding_cfg.get("provider"),
            model=embedding_cfg.get("model"),
            cache=(
                EmbeddingCacheConfig(
                    backend=cache_cfg.get("backend"),
                    uri=cache_cfg.get("uri"),
                )
                if cache_cfg
                else None
            ),
        )

    limits = None
    if limits_cfg:
        limits = ResourceLimits(
            max_vectors_per_ingest=limits_cfg.get("max_vectors_per_ingest"),
            max_k=limits_cfg.get("max_k"),
            max_query_size=limits_cfg.get("max_query_size"),
            max_execution_time_ms=limits_cfg.get("max_execution_time_ms"),
        )

    return ExecutionConfig(
        vector_store=vector_store,
        embeddings=embeddings,
        resource_limits=limits,
    )


def build_config(
    *,
    vector_store: str | None = None,
    vector_store_uri: str | None = None,
    embed_provider: str | None = None,
    embed_model: str | None = None,
    cache_embeddings: str | None = None,
    base_config: ExecutionConfig | None = None,
) -> ExecutionConfig:
    resolved_vector_store = base_config.vector_store if base_config else None
    if vector_store:
        resolved_vector_store = VectorStoreConfig(
            backend=vector_store,
            uri=vector_store_uri,
        )

    resolved_embeddings = base_config.embeddings if base_config else None
    if embed_model or embed_provider or cache_embeddings:
        cache_config = (
            EmbeddingCacheConfig(backend=None, uri=cache_embeddings)
            if cache_embeddings
            else None
        )
        resolved_embeddings = EmbeddingConfig(
            provider=embed_provider,
            model=embed_model,
            cache=cache_config,
        )

    limits = base_config.resource_limits if base_config else None
    return ExecutionConfig(
        vector_store=resolved_vector_store,
        embeddings=resolved_embeddings,
        resource_limits=limits,
    )


__all__ = [
    "ALLOWED_INTENTS",
    "build_config",
    "load_config",
    "parse_contract",
    "parse_intent",
    "parse_mode",
]
