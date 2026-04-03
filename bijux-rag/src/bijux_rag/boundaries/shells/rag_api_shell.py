# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Back-compat shim for the historical file-based API shell.

# pyright: reportUnknownArgumentType=false, reportUnknownMemberType=false, reportUnknownVariableType=false
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

from bijux_rag.boundaries.shells.rag_file_shell import RagFileShell
from bijux_rag.core.rag_types import Chunk
from bijux_rag.infra.adapters.file_storage import FileStorage
from bijux_rag.rag.stages import ChunkAndEmbedConfig
from bijux_rag.result import Err, Ok, Result


@dataclass(frozen=True)
class RagApiShell:  # pragma: no cover
    in_path: Path
    out_path: Path
    cfg: ChunkAndEmbedConfig

    def run(self) -> Result[None, str]:
        return RagFileShell(in_path=self.in_path, out_path=self.out_path, cfg=self.cfg).run()


def read_docs_csv(
    path: Path,
) -> Iterable[tuple[str, str, str | None, str | None]]:  # pragma: no cover
    return RagFileShell(in_path=path, out_path=Path("-"), cfg=ChunkAndEmbedConfig()).read_docs(path)


# Compatibility shims for legacy imports
class FSReader:
    def read_docs(self, path: str) -> Result[list, str]:
        storage = FileStorage()
        docs: list = []
        errors: list[str] = []
        for res in storage.read_docs(path):
            if isinstance(res, Ok):
                docs.append(res.value)
            elif isinstance(res, Err):
                errors.append(res.error.msg)
        if errors:
            return Err("; ".join(errors))
        return Ok(docs)


def write_chunks_jsonl(path: str, chunks: list[Chunk]) -> Result[None, str]:
    try:
        with Path(path).open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(
                    '{"doc_id":"%s","text":"%s","start":%d,"end":%d}\n'
                    % (c.doc_id, str(c.text).replace('"', '\\"'), c.start, c.end)
                )
        return Ok(None)
    except Exception as exc:  # pragma: no cover
        return Err(str(exc))


def run(input_path: str, output_path: str, cfg: ChunkAndEmbedConfig) -> Result[None, str]:
    return RagFileShell(in_path=Path(input_path), out_path=Path(output_path), cfg=cfg).run()
