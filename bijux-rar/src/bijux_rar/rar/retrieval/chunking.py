# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Deterministic document chunking with byte-span contracts.

SPDX-FileCopyrightText: © 2025 Bijan Mousavi
SPDX-License-Identifier: MIT
"""

from __future__ import annotations

from dataclasses import dataclass
import hashlib


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    doc_sha256: str
    chunk_id: str
    start_byte: int
    end_byte: int
    text: str
    title: str | None = None
    source: str | None = None


def _char_to_byte_offsets(text: str) -> list[int]:
    offsets = [0]
    total = 0
    for ch in text:
        total += len(ch.encode("utf-8"))
        offsets.append(total)
    return offsets


def chunk_document(
    *,
    doc_id: str,
    text: str,
    title: str | None = None,
    source: str | None = None,
    chunk_chars: int = 800,
    overlap_chars: int = 120,
) -> list[Chunk]:
    """Chunk deterministically by characters; spans are UTF-8 byte offsets."""
    chunk_chars = max(1, int(chunk_chars))
    overlap_chars = max(0, int(overlap_chars))
    if overlap_chars >= chunk_chars:
        overlap_chars = max(0, chunk_chars // 4)

    doc_bytes = text.encode("utf-8")
    doc_sha = hashlib.sha256(doc_bytes).hexdigest()
    offsets = _char_to_byte_offsets(text)
    n = len(text)
    step = max(1, chunk_chars - overlap_chars)

    out: list[Chunk] = []
    start_c = 0
    while start_c < n:
        end_c = min(n, start_c + chunk_chars)
        start_b = offsets[start_c]
        end_b = offsets[end_c]
        chunk_text = text[start_c:end_c]
        cid = hashlib.sha256(doc_bytes[start_b:end_b]).hexdigest()
        out.append(
            Chunk(
                doc_id=doc_id,
                doc_sha256=doc_sha,
                chunk_id=cid,
                start_byte=start_b,
                end_byte=end_b,
                text=chunk_text,
                title=title,
                source=source,
            )
        )
        if end_c >= n:
            break
        start_c += step
    return out
