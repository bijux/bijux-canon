# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.core.types import Chunk, EmbeddingSpec
from bijux_canon_ingest.interfaces.cli.pipeline_output import (
    chunk_to_json,
    render_error,
    write_chunk_results,
)
from bijux_canon_ingest.result.types import Err, ErrInfo, Ok


def test_chunk_to_json_projects_metadata_and_embedding() -> None:
    chunk = Chunk(
        doc_id="d1",
        text="alpha",
        start=0,
        end=5,
        metadata={"category": "cs.AI"},
        embedding=(0.1, 0.2),
        embedding_spec=EmbeddingSpec(model="hash16", dim=2),
    )

    payload = chunk_to_json(chunk)

    assert payload["doc_id"] == "d1"
    assert payload["metadata"] == {"category": "cs.AI"}
    assert payload["embedding"] == [0.1, 0.2]


def test_render_error_returns_parse_exit_code(capsys) -> None:
    code = render_error(Err(ErrInfo(code="PARSE_CONFIG", msg="bad", stage="config")))

    assert code == 2
    assert '"code": "PARSE_CONFIG"' in capsys.readouterr().out


def test_write_chunk_results_writes_only_successes(tmp_path: Path) -> None:
    out_path = tmp_path / "chunks.jsonl"
    chunk = Chunk(
        doc_id="d1",
        text="alpha",
        start=0,
        end=5,
        metadata={},
        embedding=(0.1,),
        embedding_spec=EmbeddingSpec(model="hash16", dim=1),
    )

    write_chunk_results(
        [
            Ok(chunk),
            Err(ErrInfo(code="PARSE_DOC", msg="skip", stage="read")),
        ],
        out_path=out_path,
    )

    lines = out_path.read_text(encoding="utf-8").splitlines()
    assert len(lines) == 1
    assert '"doc_id": "d1"' in lines[0]
