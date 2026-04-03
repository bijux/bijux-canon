# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bijux_rag.rag.stages import ChunkAndEmbedConfig, chunk_and_embed_docs
from bijux_rag.result.types import Err, Ok, Result


@dataclass(frozen=True)
class RagFileShell:
    """File-based ingestion shell (NOT HTTP API).

    # pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
    """

    in_path: Path
    out_path: Path
    cfg: ChunkAndEmbedConfig

    def run(self) -> Result[None, str]:
        docs = self._read_docs(self.in_path)
        res = chunk_and_embed_docs(docs, self.cfg)
        if isinstance(res, Err):
            return Err(res.error)
        self._write_chunks(self.out_path, res.value)
        return Ok(None)

    def read_docs(self, path: Path) -> Iterable[tuple[str, str, str | None, str | None]]:
        """Public reader for CSV docs (used by back-compat shims)."""
        return self._read_docs(path)

    def _read_docs(self, path: Path) -> Iterable[tuple[str, str, str | None, str | None]]:
        import csv

        with path.open("r", encoding="utf-8") as f:
            r = csv.DictReader(f)
            for row in r:
                yield (row["doc_id"], row["text"], row.get("title"), row.get("category"))

    def _write_chunks(self, path: Path, chunks: Iterable["Chunk"]) -> None:
        import json

        with path.open("w", encoding="utf-8") as f:
            for c in chunks:
                payload = {**dict(c.metadata), "text": c.text, "embedding": c.embedding}
                f.write(json.dumps(payload) + "\n")


# Late import to avoid circular dependency at type-check time.
from bijux_rag.core.rag_types import Chunk  # noqa: E402  isort:skip
