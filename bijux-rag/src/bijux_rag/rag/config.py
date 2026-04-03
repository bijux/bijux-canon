# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Configuration and dependency wiring for the RAG surface (end-of-Bijux RAG).

The config-as-data and dependency-wiring patterns are introduced in Bijux RAG
and extended in Bijux RAG with streaming entry points.
"""

from __future__ import annotations

from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from typing import Callable, Mapping, Protocol

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, RagEnv, RawDoc
from bijux_rag.core.rules_pred import DEFAULT_RULES, RulesConfig
from bijux_rag.rag.clean_cfg import DEFAULT_CLEAN_CONFIG, RULES, CleanConfig, make_cleaner
from bijux_rag.rag.stages import embed_chunk
from bijux_rag.rag.types import DebugConfig, Observations, RagTaps
from bijux_rag.result import Err, Ok, Result


class DocsReader(Protocol):
    def read_docs(self, path: str) -> Result[list[RawDoc], str]: ...


@dataclass(frozen=True)
class RagConfig:
    env: RagEnv
    keep: RulesConfig = DEFAULT_RULES
    clean: CleanConfig = DEFAULT_CLEAN_CONFIG
    debug: DebugConfig = DebugConfig()


@dataclass(frozen=True)
class RagCoreDeps:
    cleaner: Callable[[RawDoc], CleanDoc]
    embedder: Callable[[ChunkWithoutEmbedding], Chunk]
    taps: RagTaps | None = None


@dataclass(frozen=True)
class RagBoundaryDeps:
    core: RagCoreDeps
    reader: DocsReader


def get_deps(config: RagConfig, *, taps: RagTaps | None = None) -> RagCoreDeps:
    cleaner = make_cleaner(config.clean)
    return RagCoreDeps(cleaner=cleaner, embedder=embed_chunk, taps=taps)


def make_rag_fn(
    *,
    chunk_size: int,
    clean_cfg: CleanConfig = DEFAULT_CLEAN_CONFIG,
    keep: RulesConfig = DEFAULT_RULES,
    debug: DebugConfig | None = None,
    taps: RagTaps | None = None,
) -> Callable[[list[RawDoc]], tuple[list[Chunk], Observations]]:
    """Pure configurator: capture immutable config into a reusable callable."""

    from bijux_rag.rag.rag_api import full_rag_api

    debug_cfg = debug if debug is not None else DebugConfig()

    config = RagConfig(env=RagEnv(chunk_size), keep=keep, clean=clean_cfg, debug=debug_cfg)
    deps = get_deps(config, taps=taps)

    def run(docs: list[RawDoc]) -> tuple[list[Chunk], Observations]:
        return full_rag_api(docs, config, deps)

    return run


def make_gen_rag_fn(
    *,
    chunk_size: int,
    max_chunks: int = 10_000,
    clean_cfg: CleanConfig = DEFAULT_CLEAN_CONFIG,
    keep: RulesConfig = DEFAULT_RULES,
) -> Callable[[Iterable[RawDoc]], Iterator[ChunkWithoutEmbedding]]:
    """Pure configurator: build a streaming docs -> chunk stream function (Bijux RAG)."""

    from bijux_rag.rag.streaming_rag import gen_bounded_chunks

    config = RagConfig(env=RagEnv(chunk_size), keep=keep, clean=clean_cfg)
    deps = get_deps(config)

    def run(docs: Iterable[RawDoc]) -> Iterator[ChunkWithoutEmbedding]:
        return gen_bounded_chunks(docs, config, deps, max_chunks=max_chunks)

    return run


def boundary_rag_config(raw: Mapping[str, object]) -> Result[RagConfig, str]:
    """Parse untyped boundary config into frozen RagConfig."""

    chunk_size_raw = raw.get("chunk_size", 512)
    if not isinstance(chunk_size_raw, int):
        return Err(f"Invalid config: chunk_size must be int (got {type(chunk_size_raw).__name__})")

    rule_names_raw = raw.get("clean_rules", DEFAULT_CLEAN_CONFIG.rule_names)
    if not isinstance(rule_names_raw, (tuple, list)) or not all(
        isinstance(x, str) for x in rule_names_raw
    ):
        return Err("Invalid config: clean_rules must be list[str] or tuple[str, ...]")
    rule_names = tuple(rule_names_raw)
    missing = [name for name in rule_names if name not in RULES]
    if missing:
        available = ", ".join(sorted(RULES))
        return Err(f"Invalid config: unknown clean rule(s): {missing}; available: {available}")

    return Ok(RagConfig(env=RagEnv(chunk_size_raw), clean=CleanConfig(rule_names=rule_names)))


__all__ = [
    "DocsReader",
    "RagConfig",
    "RagCoreDeps",
    "RagBoundaryDeps",
    "get_deps",
    "make_rag_fn",
    "make_gen_rag_fn",
    "boundary_rag_config",
]
