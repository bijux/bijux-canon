# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_ingest.application.document_inputs import coerce_raw_doc, raw_docs_to_chunks
from bijux_canon_ingest.core.types import RawDoc
from bijux_canon_ingest.result import Ok


def test_coerce_raw_doc_accepts_mapping_rows() -> None:
    raw = coerce_raw_doc(
        {"doc_id": "d1", "title": "Title", "text": "alpha beta", "category": "cs.AI"}
    )

    assert raw == RawDoc("d1", "Title", "alpha beta", "cs.AI")


def test_coerce_raw_doc_rejects_unsupported_inputs() -> None:
    with pytest.raises(TypeError, match="docs must be RawDoc"):
        coerce_raw_doc(object())


def test_raw_docs_to_chunks_materializes_chunk_records() -> None:
    result = raw_docs_to_chunks(
        [RawDoc("d1", "Title", "alpha beta gamma", "cs.AI")],
        chunk_size=16,
        overlap=0,
        tail_policy="emit_short",
    )

    assert isinstance(result, Ok)
    assert result.value
