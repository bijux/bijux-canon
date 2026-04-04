# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.core.types import Chunk, EmbeddingSpec
from bijux_canon_ingest.interfaces.cli.document_pipeline_io import (
    read_csv_docs,
    write_chunk_jsonl,
)


def test_read_csv_docs_projects_expected_tuple_shape(tmp_path: Path) -> None:
    path = tmp_path / "docs.csv"
    path.write_text(
        "doc_id,text,title,category\n"
        "d1,alpha,Title,cs.AI\n",
        encoding="utf-8",
    )

    assert list(read_csv_docs(path)) == [("d1", "alpha", "Title", "cs.AI")]


def test_write_chunk_jsonl_writes_embedding_payload(tmp_path: Path) -> None:
    path = tmp_path / "chunks.jsonl"
    chunk = Chunk(
        doc_id="d1",
        text="alpha",
        start=0,
        end=5,
        metadata={"category": "cs.AI"},
        embedding=(0.1,),
        embedding_spec=EmbeddingSpec(model="hash16", dim=1),
    )

    write_chunk_jsonl(path, [chunk])

    payload = path.read_text(encoding="utf-8")
    assert '"text": "alpha"' in payload
    assert '"embedding": [0.1]' in payload
