# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Document-to-chunk shell helpers for CLI-driven ingestion."""

from __future__ import annotations

from collections.abc import Iterable
import csv
from dataclasses import dataclass
from pathlib import Path
import json

from bijux_canon_ingest.core.types import Chunk
from bijux_canon_ingest.processing.stages import ChunkAndEmbedConfig, chunk_and_embed_docs
from bijux_canon_ingest.result.types import Err, Ok, Result


@dataclass(frozen=True)
class DocumentChunkShell:
    """File-backed shell that converts CSV documents into JSONL chunks."""

    in_path: Path
    out_path: Path
    cfg: ChunkAndEmbedConfig

    def run(self) -> Result[None, str]:
        docs = self.read_docs(self.in_path)
        result = chunk_and_embed_docs(docs, self.cfg)
        if isinstance(result, Err):
            return Err(result.error)
        self.write_chunks(self.out_path, result.value)
        return Ok(None)

    def read_docs(
        self,
        path: Path,
    ) -> Iterable[tuple[str, str, str | None, str | None]]:
        with path.open("r", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            for row in reader:
                yield (
                    row["doc_id"],
                    row["text"],
                    row.get("title"),
                    row.get("category"),
                )

    def write_chunks(self, path: Path, chunks: Iterable[Chunk]) -> None:
        with path.open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                payload = {
                    **dict(chunk.metadata),
                    "text": chunk.text,
                    "embedding": list(chunk.embedding),
                }
                handle.write(json.dumps(payload, ensure_ascii=False))
                handle.write("\n")


__all__ = ["DocumentChunkShell"]
