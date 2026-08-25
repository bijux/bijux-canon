# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Installed interface parity for the canonical index application service."""

from __future__ import annotations

import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest
from typer.testing import CliRunner

from bijux_canon_index.api.v1.app import build_app
from bijux_canon_index.api.v1.runtime import generation_service
from bijux_canon_index.application import (
    IndexCompatibility,
    IndexService,
)
from bijux_canon_index.application.surface_services import (
    index_service_from_environment,
)
from bijux_canon_index.interfaces.cli.app import app as cli_app


def _build_payload(snapshot: str, *, activate: bool) -> dict[str, object]:
    return {
        "chunks": [
            {
                "chunk_id": "chunk-a",
                "document_id": "paper-a",
                "ordinal": 0,
                "text": "Ancient DNA preserves direct evidence.",
                "vector": [1.0, 0.0, 0.0],
                "metadata": {"source_id": "paper-a", "language": "en"},
            },
            {
                "chunk_id": "chunk-b",
                "document_id": "paper-b",
                "ordinal": 0,
                "text": "Genomic contamination constrains interpretation.",
                "vector": [0.0, 1.0, 0.0],
                "metadata": {"source_id": "paper-b", "language": "en"},
            },
        ],
        "snapshot_artifact_id": snapshot,
        "model_lock_artifact_id": "sha256:model-lock",
        "limits": {
            "max_chunks": 10,
            "max_text_bytes": 10000,
            "max_vector_bytes": 10000,
            "max_metadata_bytes": 10000,
        },
        "hnsw_parameters": {
            "m": 2,
            "ef_construction": 8,
            "ef_search": 8,
            "seed": 19,
        },
        "activate": activate,
    }


def test_surface_configuration_requires_a_complete_compatibility_profile(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIJUX_CANON_INDEX_GENERATION_ROOT", str(tmp_path / "registry"))
    monkeypatch.setenv("BIJUX_CANON_INDEX_CONFIGURATION_ID", "sha256:" + "f" * 64)

    with pytest.raises(ValueError, match="requires a model profile"):
        index_service_from_environment()

    monkeypatch.setenv("BIJUX_CANON_INDEX_MODEL_LOCK_ARTIFACT_ID", "sha256:model")
    monkeypatch.setenv("BIJUX_CANON_INDEX_MODEL_DIMENSION", "3")
    assert (
        index_service_from_environment().registry_root
        == (tmp_path / "registry").resolve()
    )


def test_library_cli_runtime_and_http_share_generation_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    registry_root = tmp_path / "registry"
    monkeypatch.setenv("BIJUX_CANON_INDEX_GENERATION_ROOT", str(registry_root))
    monkeypatch.setenv("BIJUX_CANON_INDEX_MODEL_LOCK_ARTIFACT_ID", "sha256:model-lock")
    monkeypatch.setenv("BIJUX_CANON_INDEX_MODEL_DIMENSION", "3")
    runner = CliRunner()
    cli_build_request = tmp_path / "cli-build.json"
    cli_build_request.write_text(
        json.dumps(_build_payload("sha256:snapshot-cli", activate=True)),
        encoding="utf-8",
    )

    cli_build = runner.invoke(
        cli_app,
        ["index", "build", "--request", str(cli_build_request)],
        prog_name="bijux",
    )
    assert cli_build.exit_code == 0, cli_build.stdout
    cli_generation = json.loads(cli_build.stdout)["generation_id"]

    client = TestClient(build_app())
    inspected = client.post(
        "/index/generations/inspect",
        json={"generation_id": cli_generation},
    )
    assert inspected.status_code == 200
    assert inspected.json()["activation"]["active"] is True
    verified = client.post(
        "/index/generations/verify",
        json={"generation_id": cli_generation},
    )
    assert verified.status_code == 200
    assert verified.json()["integrity"]["status"] == "verified"

    http_build = client.post(
        "/index/generations/build",
        json=_build_payload("sha256:snapshot-http", activate=False),
    )
    assert http_build.status_code == 200, http_build.text
    http_generation = http_build.json()["generation_id"]
    assert http_generation != cli_generation
    activated = client.post(
        "/index/generations/activate",
        json={"generation_id": http_generation},
    )
    assert activated.status_code == 200

    cli_activate = runner.invoke(
        cli_app,
        ["index", "activate", "--generation-id", http_generation],
        prog_name="bijux",
    )
    assert cli_activate.exit_code == 0, cli_activate.stdout
    assert json.loads(cli_activate.stdout)["activation"]["active"] is True

    exact_query = client.post(
        "/index/generations/query",
        json={
            "generation_id": http_generation,
            "channel": "faiss-flat-ip",
            "query_vector": [1.0, 0.0, 0.0],
            "top_k": 1,
        },
    )
    assert exact_query.status_code == 200, exact_query.text
    assert exact_query.json()["hits"][0]["chunk_id"] == "chunk-a"

    cli_query_request = tmp_path / "cli-query.json"
    cli_query_request.write_text(
        json.dumps(
            {
                "generation_id": http_generation,
                "channel": "sqlite-fts5",
                "query_text": "ancient DNA",
                "top_k": 1,
            }
        ),
        encoding="utf-8",
    )
    cli_query = runner.invoke(
        cli_app,
        ["index", "query", "--request", str(cli_query_request)],
        prog_name="bijux",
    )
    assert cli_query.exit_code == 0, cli_query.stdout
    assert json.loads(cli_query.stdout)["hits"][0]["chunk_id"] == "chunk-a"

    runtime_report = generation_service().inspect()
    library_report = IndexService(
        registry_root,
        compatibility=IndexCompatibility("sha256:model-lock", 3),
    ).inspect()
    assert runtime_report == library_report
    assert runtime_report.generation_id == http_generation


def test_generation_http_schema_and_refusal_are_explicit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setenv("BIJUX_CANON_INDEX_GENERATION_ROOT", str(tmp_path / "registry"))
    client = TestClient(build_app())
    schema = client.get("/openapi.json").json()
    operation_ids = {
        operation["operationId"]
        for path in schema["paths"].values()
        for operation in path.values()
        if isinstance(operation, dict) and "operationId" in operation
    }
    assert {
        "buildIndexGeneration",
        "activateIndexGeneration",
        "inspectIndexGeneration",
        "verifyIndexGeneration",
        "queryIndexGeneration",
    }.issubset(operation_ids)

    refused = client.post(
        "/index/generations/query",
        json={
            "channel": "sqlite-fts5",
            "query_text": "evidence",
            "query_vector": [1.0],
            "top_k": 1,
        },
    )
    assert refused.status_code == 422
