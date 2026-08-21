# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bijux_canon_ingest import (
    CanonicalIngestRequest,
    CorpusSnapshotConfiguration,
    ingest_corpus,
)
from bijux_canon_ingest.interfaces.cli.entrypoint import main
from bijux_canon_ingest.interfaces.http.app import create_app


def test_library_cli_runtime_and_http_share_result_schema(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "evidence.txt").write_text(
        "Canonical ingestion evidence shared across every installed boundary.",
        encoding="utf-8",
    )
    request = CanonicalIngestRequest(
        root_path=sources,
        root_name="interface-evidence",
        configuration=CorpusSnapshotConfiguration(corpus_name="interface-evidence"),
    )
    expected = ingest_corpus(request).manifest()

    exit_code = main(
        [
            "corpus",
            "build",
            "--root",
            str(sources),
            "--root-name",
            "interface-evidence",
            "--corpus-name",
            "interface-evidence",
        ]
    )
    cli_payload = json.loads(capsys.readouterr().out)
    response = TestClient(create_app()).post(
        "/v1/corpora/ingest",
        json={
            "root_path": str(sources),
            "root_name": "interface-evidence",
            "corpus_name": "interface-evidence",
        },
    )

    assert exit_code == 0
    assert response.status_code == 200
    assert cli_payload == expected
    assert response.json() == expected
