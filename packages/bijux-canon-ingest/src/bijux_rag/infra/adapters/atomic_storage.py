# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi <bijan@bijux.io>

"""Bijux RAG infra: atomic write-if-absent adapter for idempotent writes."""

from __future__ import annotations

from collections.abc import Iterator
import os

from bijux_rag.core.rag_types import Chunk
from bijux_rag.domain.idempotent import AtomicWriteCap
from bijux_rag.result.types import Err, ErrInfo, Ok, Result

from .file_storage import FileStorage


class AtomicFileStorage(AtomicWriteCap):
    def __init__(self, *, root: str) -> None:
        self.root = root
        self._storage = FileStorage()

    def write_if_absent(
        self, key: str, chunks: Iterator[Chunk]
    ) -> Result[bool, ErrInfo]:
        path = os.path.join(self.root, key)
        if os.path.exists(path):
            return Ok(False)
        res = self._storage.write_chunks(path, chunks)
        return Err(res.error) if isinstance(res, Err) else Ok(True)


__all__ = ["AtomicFileStorage"]
