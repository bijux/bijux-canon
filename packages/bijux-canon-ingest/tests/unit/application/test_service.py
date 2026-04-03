# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.application.service import IngestService
from bijux_canon_ingest.core.types import RawDoc
from bijux_canon_ingest.result import Ok


def _docs() -> list[RawDoc]:
    return [
        RawDoc(
            doc_id="d1",
            title="Mito",
            abstract="Mitochondria are the powerhouse of the cell.",
            categories="bio",
        ),
        RawDoc(
            doc_id="d2",
            title="Chloro",
            abstract="Chloroplasts perform photosynthesis in plants.",
            categories="bio",
        ),
    ]


def test_ask_returns_typed_payload_with_citations(tmp_path: Path) -> None:
    service = IngestService()
    build_result = service.build_index(_docs(), backend="bm25", chunk_size=64, overlap=0)
    assert isinstance(build_result, Ok)

    path = tmp_path / "index.msgpack"
    save_result = service.save_index(build_result.value, path)
    assert isinstance(save_result, Ok)

    load_result = service.load_index(path)
    assert isinstance(load_result, Ok)

    ask_result = service.ask(
        index=load_result.value,
        query="What is the powerhouse of the cell?",
        top_k=3,
        filters={},
        rerank=True,
    )
    assert isinstance(ask_result, Ok)
    assert ask_result.value["answer"]
    assert ask_result.value["citations"][0]["doc_id"] == "d1"
    assert ask_result.value["contexts"][0]["chunk_id"]


def test_ask_blob_returns_grounded_answer(tmp_path: Path) -> None:
    service = IngestService()
    build_result = service.build_index(_docs(), backend="bm25", chunk_size=64, overlap=0)
    assert isinstance(build_result, Ok)

    path = tmp_path / "index.msgpack"
    save_result = service.save_index(build_result.value, path)
    assert isinstance(save_result, Ok)

    answer_result = service.ask_blob(
        blob=path.read_bytes(),
        query="powerhouse of the cell",
        top_k=3,
        filters={},
        rerank=True,
    )
    assert isinstance(answer_result, Ok)
    assert answer_result.value.citations
    assert answer_result.value.citations[0].doc_id == "d1"
