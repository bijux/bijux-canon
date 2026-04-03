# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 5: config-driven, stateless pipelines (end-of-Bijux RAG).

This is a minimal, production-safe subset of the module text:
- a `PipelineConfig` is pure data
- `build_rag_pipeline` validates step compatibility at build time
- execution remains lazy (iterators), and errors are represented with `Result`
"""

from __future__ import annotations

from collections.abc import Callable, Iterator, Mapping
from dataclasses import dataclass, field
from itertools import chain
from typing import Any, cast

from bijux_rag.core.rag_types import Chunk, ChunkWithoutEmbedding, CleanDoc, RagEnv, RawDoc
from bijux_rag.rag.stages import clean_doc, embed_chunk, iter_chunk_doc
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


@dataclass(frozen=True, slots=True)
class StepConfig:
    name: str
    params: Mapping[str, object] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class PipelineConfig:
    steps: tuple[StepConfig, ...]

    def __post_init__(self) -> None:
        if not self.steps:
            raise ValueError("PipelineConfig.steps must be non-empty")


def _env_from_params(params: Mapping[str, object]) -> RagEnv:
    chunk_size = params.get("chunk_size", 512)
    overlap = params.get("overlap", 0)
    tail_policy = params.get("tail_policy", "emit_short")
    if (
        not isinstance(chunk_size, int)
        or not isinstance(overlap, int)
        or not isinstance(tail_policy, str)
    ):
        raise TypeError("chunk params must be: chunk_size:int, overlap:int, tail_policy:str")
    return RagEnv(chunk_size=chunk_size, overlap=overlap, tail_policy=tail_policy)


def build_rag_pipeline(
    config: PipelineConfig,
    *,
    artifacts: Mapping[str, Mapping[str, object]] | None = None,
) -> Callable[[Iterator[RawDoc]], Iterator[Result[Chunk, ErrInfo]]]:
    """Build an ingestion pipeline from config.

    Steps:
    - clean: RawDoc -> CleanDoc
    - chunk: CleanDoc -> ChunkWithoutEmbedding (flat map)
    - embed: ChunkWithoutEmbedding -> Result[Chunk, ErrInfo]
    """

    artifacts = artifacts or {}

    steps: list[tuple[str, Callable[[Any], Any]]] = []
    prev_kind: str = "RawDoc"

    for step in config.steps:
        params = dict(step.params)
        injected = dict(artifacts.get(step.name, {}))
        overlap = set(params) & set(injected)
        if overlap:
            raise ValueError(
                f"Artifact overlaps config params for step {step.name}: {sorted(overlap)}"
            )

        if step.name == "clean":
            if prev_kind != "RawDoc":
                raise TypeError("clean expects RawDoc")
            fn = clean_doc
            steps.append(("map", fn))
            prev_kind = "CleanDoc"
            continue

        if step.name == "chunk":
            if prev_kind != "CleanDoc":
                raise TypeError("chunk expects CleanDoc")
            env = _env_from_params({**params, **injected})

            def _chunk(cd: CleanDoc, *, _env: RagEnv = env) -> Iterator[ChunkWithoutEmbedding]:
                yield from iter_chunk_doc(cd, _env)

            steps.append(("flatmap", _chunk))
            prev_kind = "ChunkWithoutEmbedding"
            continue

        if step.name == "embed":
            if prev_kind != "ChunkWithoutEmbedding":
                raise TypeError("embed expects ChunkWithoutEmbedding")
            embedder_obj = injected.get("embedder")
            embedder_fn: Callable[[ChunkWithoutEmbedding], Chunk]
            if embedder_obj is None:
                embedder_fn = embed_chunk
            else:
                if not callable(embedder_obj):
                    raise TypeError("embedder artifact must be callable")
                embedder_fn = cast(Callable[[ChunkWithoutEmbedding], Chunk], embedder_obj)

            def _embed(
                x: ChunkWithoutEmbedding,
                *,
                _embedder: Callable[[ChunkWithoutEmbedding], Chunk] = embedder_fn,
            ) -> Result[Chunk, ErrInfo]:
                try:
                    return Ok(_embedder(x))
                except Exception as exc:
                    return Err(ErrInfo.from_exception(exc, stage="embed"))

            steps.append(("map", _embed))
            prev_kind = "ResultChunk"
            continue

        raise ValueError(f"Unknown step: {step.name}")

    if prev_kind != "ResultChunk":
        raise ValueError("Pipeline must end with an effect boundary returning Result")

    def pipeline(docs: Iterator[RawDoc]) -> Iterator[Result[Chunk, ErrInfo]]:
        it: Any = docs
        for kind, fn in steps:
            if kind == "map":
                it = map(fn, it)
            elif kind == "flatmap":
                it = chain.from_iterable(map(fn, it))
            else:
                raise AssertionError("unreachable")
        return cast(Iterator[Result[Chunk, ErrInfo]], it)

    return pipeline


__all__ = ["StepConfig", "PipelineConfig", "build_rag_pipeline"]
