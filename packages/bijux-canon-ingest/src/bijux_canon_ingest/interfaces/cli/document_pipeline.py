# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Document-to-chunk shell helpers for CLI-driven ingestion."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from bijux_canon_ingest.interfaces.cli.document_pipeline_io import (
    read_csv_docs,
    write_chunk_jsonl,
)
from bijux_canon_ingest.processing.stages import (
    ChunkAndEmbedConfig,
    chunk_and_embed_docs,
)
from bijux_canon_ingest.result.types import Err, Ok, Result


@dataclass(frozen=True)
class DocumentChunkShell:
    """File-backed shell that converts CSV documents into JSONL chunks."""

    in_path: Path
    out_path: Path
    cfg: ChunkAndEmbedConfig

    def run(self) -> Result[None, str]:
        docs = read_csv_docs(self.in_path)
        result = chunk_and_embed_docs(docs, self.cfg)
        if isinstance(result, Err):
            return Err(result.error)
        write_chunk_jsonl(self.out_path, result.value)
        return Ok(None)


__all__ = ["DocumentChunkShell"]
