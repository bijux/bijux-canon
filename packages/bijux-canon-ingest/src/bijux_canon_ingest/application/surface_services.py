# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Application services shared by installed ingest command surfaces."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from bijux_canon_ingest.core.types import Chunk, RawDoc
from bijux_canon_ingest.infra.adapters.file_storage import FileStorage
from bijux_canon_ingest.processing.stages import (
    ChunkAndEmbedConfig,
    chunk_and_embed_docs,
)
from bijux_canon_ingest.result.types import Err, ErrInfo, Ok, Result


def read_documents(path: Path) -> Result[list[RawDoc], ErrInfo]:
    """Read all admitted documents through the canonical storage adapter."""
    docs: list[RawDoc] = []
    for result in FileStorage().read_docs(str(path)):
        if isinstance(result, Ok):
            docs.append(result.value)
            continue
        return Err(result.error)
    return Ok(docs)


def read_documents_or_raise(path: Path) -> list[RawDoc]:
    """Read documents and collapse structured storage failures for CLI status mapping."""
    docs: list[RawDoc] = []
    errors: list[str] = []
    for result in FileStorage().read_docs(str(path)):
        if isinstance(result, Err):
            errors.append(f"{result.error.code}: {result.error.msg}")
        else:
            docs.append(result.value)
    if errors:
        raise ValueError("CSV parse failures: " + "; ".join(errors[:3]))
    return docs


def chunk_documents(
    *,
    docs: Iterable[tuple[str, str, str | None, str | None]],
    config: ChunkAndEmbedConfig,
) -> Result[list[Chunk], str]:
    """Execute the canonical document chunking stage."""
    return chunk_and_embed_docs(docs, config)


__all__ = ["chunk_documents", "read_documents", "read_documents_or_raise"]
