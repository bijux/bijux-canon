# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from bijux_canon_ingest import (
    CanonicalIngestError,
    CanonicalIngestRequest,
    CorpusSnapshotConfiguration,
    DiscoveryLimits,
    ingest_corpus,
)
from bijux_canon_ingest.application import CorpusDiscoveryLimits
from bijux_canon_ingest.interfaces.cli.entrypoint import main
from bijux_canon_ingest.interfaces.http.app import create_app


REPOSITORY_ROOT = Path(__file__).resolve().parents[4]


def test_application_translates_portable_discovery_limits() -> None:
    request = CanonicalIngestRequest.for_directory(
        root_path=Path("sources"),
        root_name="bounded",
        corpus_name="bounded",
        discovery_limits=CorpusDiscoveryLimits(max_files=7, max_total_bytes=4096),
    )

    assert request.configuration.discovery_limits == DiscoveryLimits(
        max_files=7,
        max_total_bytes=4096,
    )
    with pytest.raises(ValueError, match="positive"):
        CorpusDiscoveryLimits(max_files=0).to_domain()


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


def test_standalone_interfaces_accept_every_supported_real_format(
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = REPOSITORY_ROOT / "examples" / "document-formats" / "corpus"
    request = CanonicalIngestRequest.for_directory(
        root_path=sources,
        root_name="real-formats",
        corpus_name="real-formats",
    )
    expected = ingest_corpus(request).manifest()

    exit_code = main(
        [
            "corpus",
            "build",
            "--root",
            str(sources),
            "--root-name",
            "real-formats",
            "--corpus-name",
            "real-formats",
        ]
    )

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == expected
    assert expected["formats"] == {
        "docx": 1,
        "html": 1,
        "jats": 1,
        "markdown": 1,
        "pdf-digital": 1,
        "text": 1,
    }
    assert expected["ocr_required_count"] == 1
    assert expected["rejection_count"] == 0


def test_cli_and_http_share_explicit_lock_refusal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "evidence.txt").write_text("locked evidence", encoding="utf-8")
    lock_path = tmp_path / "corpus.lock.json"
    lock_path.write_text("{", encoding="utf-8")

    exit_code = main(
        [
            "corpus",
            "build",
            "--root",
            str(sources),
            "--root-name",
            "locked-evidence",
            "--corpus-name",
            "locked-evidence",
            "--corpus-lock",
            str(lock_path),
        ]
    )
    cli_error = capsys.readouterr().err
    response = TestClient(create_app()).post(
        "/v1/corpora/ingest",
        json={
            "root_path": str(sources),
            "root_name": "locked-evidence",
            "corpus_name": "locked-evidence",
            "corpus_lock_path": str(lock_path),
        },
    )

    assert exit_code == 2
    assert "malformed_lock" in cli_error
    assert response.status_code == 400
    assert "malformed_lock" in response.json()["detail"]


def test_python_cli_and_http_share_discovery_limit_refusal(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / "a.txt").write_text("first", encoding="utf-8")
    (sources / "b.txt").write_text("second", encoding="utf-8")
    request = CanonicalIngestRequest(
        root_path=sources,
        root_name="bounded-evidence",
        configuration=CorpusSnapshotConfiguration(
            corpus_name="bounded-evidence",
            discovery_limits=DiscoveryLimits(max_files=1),
        ),
    )

    with pytest.raises(CanonicalIngestError, match="file_count_limit_exceeded"):
        ingest_corpus(request)
    exit_code = main(
        [
            "corpus",
            "build",
            "--root",
            str(sources),
            "--root-name",
            "bounded-evidence",
            "--corpus-name",
            "bounded-evidence",
            "--max-files",
            "1",
        ]
    )
    cli_error = capsys.readouterr().err
    response = TestClient(create_app()).post(
        "/v1/corpora/ingest",
        json={
            "root_path": str(sources),
            "root_name": "bounded-evidence",
            "corpus_name": "bounded-evidence",
            "max_files": 1,
        },
    )

    assert exit_code == 2
    assert "file_count_limit_exceeded" in cli_error
    assert response.status_code == 400
    assert "file_count_limit_exceeded" in response.json()["detail"]


def test_explicit_legacy_csv_command_preserves_implicit_pipeline(
    tmp_path: Path,
) -> None:
    source = tmp_path / "documents.csv"
    source.write_text(
        "doc_id,title,abstract,categories\n"
        "evidence-1,Release evidence,Stable compatibility output,release\n",
        encoding="utf-8",
    )
    config = tmp_path / "pipeline.json"
    config.write_text(
        json.dumps(
            {
                "steps": [
                    {"name": "clean", "params": {}},
                    {
                        "name": "chunk",
                        "params": {
                            "chunk_size": 64,
                            "overlap": 0,
                            "tail_policy": "emit_short",
                        },
                    },
                    {"name": "embed", "params": {}},
                ]
            }
        ),
        encoding="utf-8",
    )
    implicit = tmp_path / "implicit.jsonl"
    explicit = tmp_path / "explicit.jsonl"

    assert main([str(source), "--config", str(config), "--out", str(implicit)]) == 0
    assert (
        main(
            [
                "legacy-csv",
                str(source),
                "--config",
                str(config),
                "--out",
                str(explicit),
            ]
        )
        == 0
    )
    assert explicit.read_bytes() == implicit.read_bytes()
