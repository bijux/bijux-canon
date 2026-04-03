# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.rar.retrieval.chunking import chunk_document


def test_chunk_document_uses_utf8_byte_spans_and_stable_ids() -> None:
    text = "Café naïve π"  # multi-byte characters

    chunks_a = chunk_document(
        doc_id="d1", text=text, chunk_chars=5, overlap_chars=1
    )
    chunks_b = chunk_document(
        doc_id="d1", text=text, chunk_chars=5, overlap_chars=1
    )

    assert len(chunks_a) == len(chunks_b) > 1
    # stable chunk IDs and identical byte spans
    assert [(c.chunk_id, c.start_byte, c.end_byte) for c in chunks_a] == [
        (c.chunk_id, c.start_byte, c.end_byte) for c in chunks_b
    ]

    # each chunk covers a valid UTF-8 byte slice
    data = text.encode("utf-8")
    for ch in chunks_a:
        assert 0 <= ch.start_byte < ch.end_byte <= len(data)
        slice_bytes = data[ch.start_byte : ch.end_byte]
        # slice must decode without error because spans align on UTF-8 boundaries
        slice_bytes.decode("utf-8")


def test_chunk_document_overlap_changes_ids() -> None:
    text = "abcdefghij"
    chunks_small_overlap = chunk_document(
        doc_id="d1", text=text, chunk_chars=4, overlap_chars=1
    )
    chunks_large_overlap = chunk_document(
        doc_id="d1", text=text, chunk_chars=4, overlap_chars=3
    )

    ids_small = {c.chunk_id for c in chunks_small_overlap}
    ids_large = {c.chunk_id for c in chunks_large_overlap}
    # different overlap config must produce different chunk identities
    assert ids_small != ids_large
