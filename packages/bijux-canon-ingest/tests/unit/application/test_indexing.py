# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.application.indexing import (
    IndexBuildConfig,
    build_index_from_docs,
)
from bijux_canon_ingest.core.types import RagEnv, RawDoc


def test_build_index_from_docs_writes_bm25_index(tmp_path: Path) -> None:
    out_path = tmp_path / "index.msgpack"
    docs = [
        RawDoc(
            doc_id="d1", title="Title", abstract="alpha beta gamma", categories="cs.AI"
        )
    ]

    fingerprint = build_index_from_docs(
        docs=docs,
        out_path=str(out_path),
        cfg=IndexBuildConfig(chunk_env=RagEnv(chunk_size=16, overlap=0)),
    )

    assert out_path.exists()
    assert fingerprint
