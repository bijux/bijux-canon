# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG infra: filesystem storage adapter (CSV in, JSONL out).

This adapter is resource-safe:
- reads are implemented as a resource-owning iterator (generator + `with open`)
- shells should use `contextlib.closing(...)` for deterministic close on partial consumption
- writes are atomic via temp+fsync+rename
"""

from __future__ import annotations

import csv
import json
import os
import tempfile
from collections.abc import Iterator
from contextlib import ExitStack
from dataclasses import asdict

from bijux_rag.core.rag_types import Chunk, RawDoc
from bijux_rag.domain.capabilities import Storage
from bijux_rag.result.types import Err, ErrInfo, Ok, Result


def _chunk_to_jsonable(c: Chunk) -> dict[str, object]:
    d = asdict(c)
    if isinstance(d.get("metadata"), dict):
        return d
    meta = c.metadata
    d["metadata"] = dict(meta)
    return d


class FileStorage(Storage):
    def read_docs(self, path: str) -> Iterator[Result[RawDoc, ErrInfo]]:
        try:
            with open(path, newline="", encoding="utf-8") as f_in:
                reader = csv.DictReader(f_in)
                for row_num, row in enumerate(reader, start=1):
                    try:
                        yield Ok(RawDoc(**row))
                    except Exception as ex:
                        yield Err(
                            ErrInfo(
                                code="PARSE_ROW",
                                msg=str(ex),
                                stage="storage.read_docs",
                                ctx={"row": row_num, "raw_row": dict(row)},
                            )
                        )
        except OSError as ex:
            yield Err(ErrInfo(code="IO_READ", msg=str(ex), stage="storage.read_docs"))

    def write_chunks(self, path: str, chunks: Iterator[Chunk]) -> Result[None, ErrInfo]:
        tmp_path: str | None = None
        try:
            with ExitStack() as stack:
                tmp_dir = os.path.dirname(path) or "."
                tmp = stack.enter_context(
                    tempfile.NamedTemporaryFile(
                        mode="w", dir=tmp_dir, delete=False, encoding="utf-8"
                    )
                )
                tmp_path = tmp.name
                for c in chunks:
                    json.dump(_chunk_to_jsonable(c), tmp, ensure_ascii=False)
                    tmp.write("\n")
                tmp.flush()
                os.fsync(tmp.fileno())
            os.replace(tmp_path, path)
            return Ok(None)
        except Exception as ex:
            if tmp_path and os.path.exists(tmp_path):
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
            if isinstance(ex, OSError):
                return Err(ErrInfo(code="IO_WRITE", msg=str(ex), stage="storage.write_chunks"))
            return Err(ErrInfo(code="WRITE_FAILED", msg=str(ex), stage="storage.write_chunks"))


__all__ = ["FileStorage"]
