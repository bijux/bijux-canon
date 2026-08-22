# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""CSV document input and chunk JSONL output helpers for the document shell."""

from __future__ import annotations

from collections.abc import Iterable, Iterator
import csv
import json
from pathlib import Path

from bijux_canon_ingest.core.types import Chunk


def read_csv_docs(path: Path) -> Iterator[tuple[str, str, str | None, str | None]]:
    """Read document tuples from a CSV file."""

    with path.open("r", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        for row in reader:
            yield (
                row["doc_id"],
                row["text"],
                row.get("title"),
                row.get("category"),
            )


def write_chunk_jsonl(path: Path, chunks: Iterable[Chunk]) -> None:
    """Write chunks to newline-delimited JSON for CLI consumption."""

    with path.open("w", encoding="utf-8") as handle:
        for chunk in chunks:
            payload = {
                **dict(chunk.metadata),
                "text": chunk.text,
                "embedding": list(chunk.embedding),
            }
            handle.write(json.dumps(payload, ensure_ascii=False))
            handle.write("\n")


__all__ = ["read_csv_docs", "write_chunk_jsonl"]
