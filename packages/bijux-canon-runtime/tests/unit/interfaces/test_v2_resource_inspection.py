# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import argparse
from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from typing import cast

from fastapi.testclient import TestClient
import pytest

from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.operations import (
    ApplicationOperation,
    RuntimeApplicationServicesV2,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import (
    EXIT_MISSING_CAPABILITY,
    run_v2_command,
)
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobError,
    DurableJobManager,
)
from bijux_canon_runtime.runtime.inspection import RuntimeRunInspector

pytestmark = pytest.mark.unit

_CORPUS_ID = ArtifactID("sha256:" + "a" * 64)
_INDEX_ID = ArtifactID("sha256:" + "b" * 64)

_OPERATION_SURFACES = {
    "ask": ("ask", ("post", "/api/v2/answers")),
    "cancel": ("cancel", ("post", "/api/v2/jobs/{job_id}/cancellation")),
    "compare": ("compare", ("post", "/api/v2/comparisons")),
    "corpus.inspect": ("corpus-inspect", ("get", "/api/v2/corpora/{corpus_id}")),
    "corpus.prepare": ("ingest", ("post", "/api/v2/corpora/prepare")),
    "index.build": ("index", ("post", "/api/v2/indexes/build")),
    "index.inspect": ("index-inspect", ("get", "/api/v2/indexes/{index_id}")),
    "inspect": ("inspect", ("get", "/api/v2/runs/{run_id}")),
    "replay": ("replay", ("post", "/api/v2/runs/{run_id}/replays")),
    "research": ("research", ("post", "/api/v2/research")),
    "result": ("result", ("get", "/api/v2/jobs/{job_id}/result")),
    "retrieve": ("retrieve", ("post", "/api/v2/retrievals")),
    "run": ("run", ("post", "/api/v2/runs")),
    "status": ("status", ("get", "/api/v2/jobs/{job_id}")),
}


def _corpus_inspection(artifact_id: ArtifactID) -> Mapping[str, object]:
    assert artifact_id == _CORPUS_ID
    return {
        "byte_length": 421,
        "canonical_sha256": "c" * 64,
        "generation_name": "a" * 64,
        "schema_version": "bijux.canon.ingest.corpus_publication.v1",
        "snapshot_id": str(artifact_id),
    }


def _index_inspection(artifact_id: ArtifactID) -> Mapping[str, object]:
    assert artifact_id == _INDEX_ID
    return {
        "activation": {"active": True, "active_generation_id": str(artifact_id)},
        "chunk_count": 345,
        "chunk_set_sha256": "d" * 64,
        "compatibility": {"status": "compatible"},
        "dimension": 384,
        "filters": {"applied_at_query_time": True},
        "generation_id": str(artifact_id),
        "integrity": {"checks": ["manifest"], "status": "verified"},
        "lineage": {"parent_generation_id": None},
        "metadata_bytes": 32,
        "model_lock_artifact_id": "sha256:" + "e" * 64,
        "schema_version": "bijux.canon.index.inspection.v1",
        "segments": [],
        "snapshot_artifact_id": "sha256:real-derived-345",
        "text_bytes": 8192,
        "vector_bytes": 529920,
    }


def _services(*, configured: bool = True) -> RuntimeApplicationServicesV2:
    return RuntimeApplicationServicesV2(
        jobs=cast(DurableJobManager, object()),
        inspector=cast(RuntimeRunInspector, object()),
        corpus_inspector=_corpus_inspection if configured else None,
        index_inspector=_index_inspection if configured else None,
    )


def test_library_cli_and_http_publish_the_same_operation_inventory() -> None:
    parser = build_parser(prog_name="bijux-canon-runtime")
    root_subparsers = next(
        action
        for action in parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    v2_parser = root_subparsers.choices["v2"]
    v2_subparsers = next(
        action
        for action in v2_parser._actions
        if isinstance(action, argparse._SubParsersAction)
    )
    cli_commands = set(v2_subparsers.choices)
    openapi = create_app(_services()).openapi()

    assert {operation.value for operation in ApplicationOperation} == set(
        _OPERATION_SURFACES
    )
    assert {command for command, _ in _OPERATION_SURFACES.values()} < cli_commands
    assert "discover" in cli_commands
    for _, (method, path) in _OPERATION_SURFACES.values():
        assert method in openapi["paths"][path]


def test_discover_command_uses_the_ingest_application_boundary(
    tmp_path: Path,
) -> None:
    (tmp_path / "evidence.txt").write_text(
        "Ancient DNA evidence.\n",
        encoding="utf-8",
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", "discover", str(tmp_path), "--root-name", "research"]
    )
    stdout = StringIO()

    with redirect_stdout(stdout):
        assert run_v2_command(args, services=None) == 0

    payload = json.loads(stdout.getvalue())
    assert payload["schema_version"] == "bijux.canon.ingest.discovery.v1"
    assert payload["sources"][0]["relative_path"] == "evidence.txt"


@pytest.mark.parametrize(
    ("command", "artifact_id", "path"),
    [
        ("corpus-inspect", _CORPUS_ID, "/api/v2/corpora/"),
        ("index-inspect", _INDEX_ID, "/api/v2/indexes/"),
    ],
)
def test_cli_and_http_return_identical_resource_inspections(
    command: str,
    artifact_id: ArtifactID,
    path: str,
) -> None:
    services = _services()
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", command, str(artifact_id)]
    )
    stdout = StringIO()
    with redirect_stdout(stdout):
        assert run_v2_command(args, services=services) == 0
    cli_payload = json.loads(stdout.getvalue())

    response = TestClient(create_app(services)).get(
        path + str(artifact_id), headers={"Bijux-API-Version": "v2"}
    )

    assert response.status_code == 200
    assert response.json() == cli_payload


def test_missing_resource_inspector_has_equivalent_transport_error() -> None:
    services = _services(configured=False)
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", "corpus-inspect", str(_CORPUS_ID)]
    )
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert run_v2_command(args, services=services) == EXIT_MISSING_CAPABILITY
    cli_problem = json.loads(stderr.getvalue())

    response = TestClient(create_app(services)).get(
        f"/api/v2/corpora/{_CORPUS_ID}",
        headers={"Bijux-API-Version": "v2"},
    )

    assert response.status_code == 503
    http_problem = response.json()
    assert cli_problem["code"] == http_problem["code"] == "missing-capability"
    assert cli_problem["retryable"] is http_problem["retryable"] is True
    assert cli_problem["remediation"] == http_problem["remediation"]
    assert cli_problem["cause"] == http_problem["cause"]


def test_invalid_resource_identity_has_equivalent_transport_error() -> None:
    services = _services()
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", "index-inspect", "not-an-artifact"]
    )
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert run_v2_command(args, services=services) == 2
    cli_problem = json.loads(stderr.getvalue())

    response = TestClient(create_app(services)).get(
        "/api/v2/indexes/not-an-artifact",
        headers={"Bijux-API-Version": "v2"},
    )

    assert response.status_code == 400
    http_problem = response.json()
    assert cli_problem["code"] == http_problem["code"] == "invalid-request"
    assert cli_problem["retryable"] is http_problem["retryable"] is False
    assert cli_problem["cause"] == http_problem["cause"]


@pytest.mark.parametrize(
    ("error", "exit_code", "status_code", "code", "retryable"),
    [
        (KeyError("missing corpus"), 4, 404, "not-found", False),
        (DurableJobError("immutable conflict"), 4, 409, "conflict", False),
        (RuntimeError("execution failed"), 4, 500, "operation-failed", True),
    ],
)
def test_application_failures_have_equivalent_transport_errors(
    error: Exception,
    exit_code: int,
    status_code: int,
    code: str,
    retryable: bool,
) -> None:
    def fail(_: ArtifactID) -> Mapping[str, object]:
        raise error

    services = RuntimeApplicationServicesV2(
        jobs=cast(DurableJobManager, object()),
        inspector=cast(RuntimeRunInspector, object()),
        corpus_inspector=fail,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", "corpus-inspect", str(_CORPUS_ID)]
    )
    stderr = StringIO()
    with redirect_stderr(stderr):
        assert run_v2_command(args, services=services) == exit_code
    cli_problem = json.loads(stderr.getvalue())

    response = TestClient(create_app(services), raise_server_exceptions=False).get(
        f"/api/v2/corpora/{_CORPUS_ID}", headers={"Bijux-API-Version": "v2"}
    )

    assert response.status_code == status_code
    http_problem = response.json()
    for field in ("code", "retryable", "remediation", "cause"):
        assert cli_problem[field] == http_problem[field]
    assert cli_problem["code"] == code
    assert cli_problem["retryable"] is retryable
