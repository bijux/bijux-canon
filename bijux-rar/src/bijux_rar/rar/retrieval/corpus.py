# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Corpus helpers for deterministic local retrieval.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from collections.abc import Iterator
from dataclasses import dataclass
import json
from pathlib import Path


@dataclass(frozen=True)
class CorpusDoc:
    """A single corpus document."""

    doc_id: str
    text: str
    title: str | None = None
    source: str | None = None


def load_corpus_jsonl(path: Path) -> list[CorpusDoc]:
    """Load a small local corpus from JSONL."""
    return list(load_corpus_jsonl_stream(path))


def load_corpus_jsonl_stream(
    path: Path, *, max_bytes: int | None = None, max_docs: int | None = None
) -> Iterator[CorpusDoc]:
    """Stream corpus docs line-by-line to avoid loading the whole file into memory."""
    bytes_read = 0
    doc_count = 0
    with path.open("r", encoding="utf-8") as fh:
        for i, raw_line in enumerate(fh):
            line = raw_line.strip()
            bytes_read += len(raw_line.encode("utf-8"))
            if max_bytes is not None and max_bytes > 0 and bytes_read > max_bytes:
                raise ValueError(f"Corpus exceeds max_bytes={max_bytes}")
            if not line:
                continue
            if max_docs is not None and max_docs > 0 and doc_count >= max_docs:
                raise ValueError(f"Corpus exceeds max_docs={max_docs}")
            try:
                obj = json.loads(line)
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON at line {i + 1} in {path}") from e
            if not isinstance(obj, dict):
                raise ValueError(f"Invalid corpus line {i + 1}: expected object")

            doc_id = obj.get("doc_id")
            text = obj.get("text")
            if not isinstance(doc_id, str) or not doc_id.strip():
                raise ValueError(f"Invalid corpus line {i + 1}: missing/empty doc_id")
            if not isinstance(text, str) or not text.strip():
                raise ValueError(f"Invalid corpus line {i + 1}: missing/empty text")
            title = obj.get("title")
            source = obj.get("source")
            yield CorpusDoc(
                doc_id=doc_id.strip(),
                text=text,
                title=title if isinstance(title, str) else None,
                source=source if isinstance(source, str) else None,
            )
            doc_count += 1
