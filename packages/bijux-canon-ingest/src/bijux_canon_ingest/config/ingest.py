# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Configuration and dependency wiring for the ingest pipeline surface."""

from __future__ import annotations

from collections.abc import Callable, Iterable, Iterator, Mapping
from dataclasses import dataclass
from typing import Protocol

from bijux_canon_ingest.core.types import (
    Chunk,
    ChunkWithoutEmbedding,
    CleanDoc,
    RagEnv,
    RawDoc,
)
from bijux_canon_ingest.core.rules_pred import DEFAULT_RULES, RulesConfig
from bijux_canon_ingest.config.cleaning import (
    DEFAULT_CLEAN_CONFIG,
    RULES,
    CleanConfig,
    make_cleaner,
)
from bijux_canon_ingest.observability import (
    DebugConfig,
    IngestTaps,
    Observations,
)
from bijux_canon_ingest.processing.stages import embed_chunk
from bijux_canon_ingest.result import Err, Ok, Result


class DocsReader(Protocol):
    def read_docs(self, path: str) -> Result[list[RawDoc], str]: ...


@dataclass(frozen=True)
class IngestConfig:
    env: RagEnv
    keep: RulesConfig = DEFAULT_RULES
    clean: CleanConfig = DEFAULT_CLEAN_CONFIG
    debug: DebugConfig = DebugConfig()


@dataclass(frozen=True)
class IngestDeps:
    cleaner: Callable[[RawDoc], CleanDoc]
    embedder: Callable[[ChunkWithoutEmbedding], Chunk]
    taps: IngestTaps | None = None


@dataclass(frozen=True)
class IngestBoundaryDeps:
    core: IngestDeps
    reader: DocsReader


def build_ingest_deps(
    config: IngestConfig,
    *,
    taps: IngestTaps | None = None,
) -> IngestDeps:
    cleaner = make_cleaner(config.clean)
    return IngestDeps(cleaner=cleaner, embedder=embed_chunk, taps=taps)


def make_ingest_fn(
    *,
    chunk_size: int,
    clean_cfg: CleanConfig = DEFAULT_CLEAN_CONFIG,
    keep: RulesConfig = DEFAULT_RULES,
    debug: DebugConfig | None = None,
    taps: IngestTaps | None = None,
) -> Callable[[list[RawDoc]], tuple[list[Chunk], Observations]]:
    """Pure configurator: capture immutable config into a reusable callable."""

    from bijux_canon_ingest.application.pipeline import run_ingest_pipeline

    debug_cfg = debug if debug is not None else DebugConfig()

    config = IngestConfig(
        env=RagEnv(chunk_size), keep=keep, clean=clean_cfg, debug=debug_cfg
    )
    deps = build_ingest_deps(config, taps=taps)

    def run(docs: list[RawDoc]) -> tuple[list[Chunk], Observations]:
        return run_ingest_pipeline(docs, config, deps)

    return run


def make_chunk_stream_fn(
    *,
    chunk_size: int,
    max_chunks: int = 10_000,
    clean_cfg: CleanConfig = DEFAULT_CLEAN_CONFIG,
    keep: RulesConfig = DEFAULT_RULES,
) -> Callable[[Iterable[RawDoc]], Iterator[ChunkWithoutEmbedding]]:
    """Pure configurator that builds a streaming docs -> chunk stream function."""

    from bijux_canon_ingest.processing.streaming import gen_bounded_chunks

    config = IngestConfig(env=RagEnv(chunk_size), keep=keep, clean=clean_cfg)
    deps = build_ingest_deps(config)

    def run(docs: Iterable[RawDoc]) -> Iterator[ChunkWithoutEmbedding]:
        return gen_bounded_chunks(docs, config, deps, max_chunks=max_chunks)

    return run


def parse_ingest_config(raw: Mapping[str, object]) -> Result[IngestConfig, str]:
    """Parse untyped boundary config into frozen IngestConfig."""

    chunk_size_raw = raw.get("chunk_size", 512)
    if not isinstance(chunk_size_raw, int):
        return Err(
            f"Invalid config: chunk_size must be int (got {type(chunk_size_raw).__name__})"
        )

    rule_names_raw = raw.get("clean_rules", DEFAULT_CLEAN_CONFIG.rule_names)
    if not isinstance(rule_names_raw, (tuple, list)) or not all(
        isinstance(x, str) for x in rule_names_raw
    ):
        return Err("Invalid config: clean_rules must be list[str] or tuple[str, ...]")
    rule_names = tuple(rule_names_raw)
    missing = [name for name in rule_names if name not in RULES]
    if missing:
        available = ", ".join(sorted(RULES))
        return Err(
            f"Invalid config: unknown clean rule(s): {missing}; available: {available}"
        )

    return Ok(
        IngestConfig(env=RagEnv(chunk_size_raw), clean=CleanConfig(rule_names=rule_names))
    )


__all__ = [
    "DocsReader",
    "IngestConfig",
    "IngestDeps",
    "IngestBoundaryDeps",
    "build_ingest_deps",
    "make_ingest_fn",
    "make_chunk_stream_fn",
    "parse_ingest_config",
]
