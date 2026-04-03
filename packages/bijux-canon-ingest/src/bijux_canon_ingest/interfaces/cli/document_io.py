# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Document IO helpers shared by CLI adapters."""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import json
from pathlib import Path

from bijux_canon_ingest.core.types import Chunk
from bijux_canon_ingest.infra.adapters.file_storage import FileStorage
from bijux_canon_ingest.interfaces.cli.document_pipeline import DocumentChunkShell
from bijux_canon_ingest.processing.stages import ChunkAndEmbedConfig
from bijux_canon_ingest.result import Err, Ok, Result


@dataclass(frozen=True)
class DocumentChunkApi:
    in_path: Path
    out_path: Path
    cfg: ChunkAndEmbedConfig

    def run(self) -> Result[None, str]:
        return DocumentChunkShell(
            in_path=self.in_path,
            out_path=self.out_path,
            cfg=self.cfg,
        ).run()


def read_docs_csv(
    path: Path,
) -> Iterable[tuple[str, str, str | None, str | None]]:
    return DocumentChunkShell(
        in_path=path,
        out_path=Path("-"),
        cfg=ChunkAndEmbedConfig(),
    ).read_docs(path)


class CsvDocumentReader:
    def read_docs(self, path: str) -> Result[list, str]:
        storage = FileStorage()
        docs: list = []
        errors: list[str] = []
        for result in storage.read_docs(path):
            if isinstance(result, Ok):
                docs.append(result.value)
            elif isinstance(result, Err):
                errors.append(result.error.msg)
        if errors:
            return Err("; ".join(errors))
        return Ok(docs)


def write_chunks_jsonl(path: str, chunks: list[Chunk]) -> Result[None, str]:
    try:
        with Path(path).open("w", encoding="utf-8") as handle:
            for chunk in chunks:
                handle.write(
                    json.dumps(
                        {
                            "doc_id": chunk.doc_id,
                            "text": chunk.text,
                            "start": chunk.start,
                            "end": chunk.end,
                        },
                        ensure_ascii=False,
                    )
                )
                handle.write("\n")
        return Ok(None)
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def run(
    input_path: str,
    output_path: str,
    cfg: ChunkAndEmbedConfig,
) -> Result[None, str]:
    return DocumentChunkShell(
        in_path=Path(input_path),
        out_path=Path(output_path),
        cfg=cfg,
    ).run()


# Compatibility aliases for older imports.
FSReader = CsvDocumentReader
IngestApiShell = DocumentChunkApi

__all__ = [
    "CsvDocumentReader",
    "DocumentChunkApi",
    "FSReader",
    "IngestApiShell",
    "read_docs_csv",
    "run",
    "write_chunks_jsonl",
]
