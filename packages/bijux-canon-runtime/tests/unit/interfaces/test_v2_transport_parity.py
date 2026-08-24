# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Mapping
from contextlib import redirect_stderr, redirect_stdout
import importlib
from io import StringIO
import json
from pathlib import Path

from fastapi.testclient import TestClient
import pytest

from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.operations import (
    ReplayOperationRequest,
    RuntimeApplicationServicesV2,
)
from bijux_canon_runtime.application.problems import (
    RuntimeProblemCode,
    runtime_problem,
    runtime_problem_fields,
)
from bijux_canon_runtime.application.runtime_configuration import RuntimeConfiguration
from bijux_canon_runtime.interfaces.cli import v2_commands
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import run_v2_command
from bijux_canon_runtime.model.execution.request_plan import RuntimeOperationRequest
from bijux_canon_runtime.ontology.ids import ArtifactID
from bijux_canon_runtime.runtime.execution.durable_jobs import (
    DurableJobSnapshot,
    JobKind,
    JobStatus,
)

pytestmark = pytest.mark.unit
v2_app_module = importlib.import_module("bijux_canon_runtime.api.v2.app")

_CORPUS_ID = "sha256:" + "a" * 64
_INDEX_ID = "sha256:" + "b" * 64
_RUN_ID = "run_v1_parity"
_ATTEMPT_ID = "attempt_v1_parity"
_IDEMPOTENCY_KEY = "transport-parity-key-0001"


def _context(name: str) -> dict[str, object]:
    return {
        "contract_version": "v2",
        "correlation_id": f"correlation-{name}",
        "replay_mode": "strict",
        "request_id": f"request-{name}",
    }


def _budget() -> dict[str, object]:
    return {"max_artifact_bytes": 1_000_000, "timeout_seconds": 30}


def _answer_policy() -> dict[str, object]:
    return {
        "permit_insufficient_answer": True,
        "provider": "local-recorded",
        "publish": True,
        "require_citations": True,
    }


def _request_payloads(tmp_path: Path) -> dict[str, dict[str, object]]:
    common = {
        "budget": _budget(),
        "execution_profile": "local-hybrid-exact",
        "scope": "ancient-dna",
    }
    retrieval = {
        **common,
        "filters": {"document_ids": [], "source_uris": []},
        "index_id": _INDEX_ID,
        "query": "What evidence supports steppe ancestry?",
        "top_k": 5,
    }
    answer = {
        **retrieval,
        "answer_policy": _answer_policy(),
        "corpus_id": _CORPUS_ID,
    }
    return {
        "ask": {**answer, "context": _context("ask")},
        "index": {**common, "context": _context("index"), "corpus_id": _CORPUS_ID},
        "ingest": {
            **common,
            "context": _context("ingest"),
            "source_directory": str(tmp_path.resolve()),
        },
        "research": {**answer, "context": _context("research")},
        "retrieve": {**retrieval, "context": _context("retrieve")},
        "run": {
            **common,
            "answer_policy": _answer_policy(),
            "context": _context("run"),
            "corpus_id": _CORPUS_ID,
            "filters": {"document_ids": [], "source_uris": []},
            "query": "What evidence supports steppe ancestry?",
            "top_k": 5,
        },
    }


def _snapshot(
    kind: JobKind,
    *,
    cancelled: bool = False,
    status: JobStatus | None = None,
) -> DurableJobSnapshot:
    effective_status = (
        JobStatus.CANCELLED
        if cancelled
        else status
        if status is not None
        else JobStatus.QUEUED
    )
    finished = effective_status in {
        JobStatus.SUCCEEDED,
        JobStatus.FAILED,
        JobStatus.CANCELLED,
        JobStatus.TIMED_OUT,
    }
    return DurableJobSnapshot(
        job_id="job_v1_transport_parity",
        kind=kind,
        idempotency_key=_IDEMPOTENCY_KEY,
        request_sha256="c" * 64,
        status=effective_status,
        cancel_requested=cancelled,
        attempt_count=0,
        submitted_at="2026-08-22T00:00:00+00:00",
        started_at="2026-08-22T00:00:00+00:00" if finished else None,
        finished_at="2026-08-22T00:00:01+00:00" if finished else None,
        deadline_at="2026-08-22T00:00:30+00:00",
        timeout_seconds=30,
        request_artifact_id="sha256:" + "a" * 64,
        result_artifact_id=None,
        result=None,
        error_type=None,
        error_message=None,
    )


class _RecordingServices(RuntimeApplicationServicesV2):
    def __init__(self) -> None:
        self.calls: list[object] = []

    def _submit(self, name: str, request: RuntimeOperationRequest, key: str):
        self.calls.append((name, request, key))
        return _snapshot(JobKind.RUN)

    def corpus(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("corpus.prepare", request, idempotency_key)

    def index(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("index.build", request, idempotency_key)

    def retrieve(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("retrieve", request, idempotency_key)

    def ask(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("ask", request, idempotency_key)

    def research(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("research", request, idempotency_key)

    def run(self, request: RuntimeOperationRequest, *, idempotency_key: str):
        return self._submit("run", request, idempotency_key)

    def replay(
        self,
        request: ReplayOperationRequest,
        *,
        idempotency_key: str,
        timeout_seconds: float | None = None,
    ):
        self.calls.append(("replay", request, idempotency_key, timeout_seconds))
        return _snapshot(JobKind.REPLAY)

    def status(self, job_id: str):
        self.calls.append(("status", job_id))
        return _snapshot(JobKind.RUN)

    def wait(self, job_id: str, *, timeout_seconds: float | None = None):
        self.calls.append(("wait", job_id, timeout_seconds))
        return _snapshot(JobKind.RUN, status=JobStatus.SUCCEEDED)

    def result(self, job_id: str):
        self.calls.append(("result", job_id))
        return {"artifact_id": _INDEX_ID, "status": "complete"}

    def cancel(self, job_id: str):
        self.calls.append(("cancel", job_id))
        return _snapshot(JobKind.RUN, cancelled=True)

    def inspect(self, run_id: str, *, attempt_id: str | None = None):
        self.calls.append(("inspect", run_id, attempt_id))
        values = [{"sequence": index} for index in range(4)]
        return {
            "artifacts": values,
            "events": values,
            "run_id": run_id,
            "selected_attempt_id": attempt_id,
            "steps": values,
        }

    def read_artifact_payload_page(
        self,
        artifact_id: ArtifactID,
        *,
        offset: int = 0,
        max_bytes: int = 64 * 1024,
    ):
        self.calls.append(("artifact.payload", artifact_id, offset, max_bytes))
        return {
            "artifact_id": str(artifact_id),
            "byte_length": 4,
            "data_base64": "dGVzdA==",
            "media_type": "text/plain",
            "next_offset": None,
            "offset": offset,
            "payload_sha256": "f" * 64,
            "schema_version": "bijux.runtime.artifact-payload-page.v1",
            "total_bytes": 4,
        }

    def compare(self, **kwargs):
        self.calls.append(("compare", kwargs))
        return {
            "baseline_run_id": kwargs["baseline_run_id"],
            "candidate_run_id": kwargs["candidate_run_id"],
            "comparison_sha256": "f" * 64,
            "differences": [{"dimension": f"dimension-{index}"} for index in range(4)],
            "equivalent": True,
            "schema_version": "bijux.runtime.comparison.v1",
        }

    def inspect_corpus(self, corpus_id: ArtifactID):
        self.calls.append(("corpus.inspect", corpus_id))
        return {
            "byte_length": 100,
            "canonical_sha256": "d" * 64,
            "generation_name": "a" * 64,
            "schema_version": "bijux.canon.ingest.corpus_publication.v1",
            "snapshot_id": str(corpus_id),
        }

    def inspect_index(self, index_id: ArtifactID):
        self.calls.append(("index.inspect", index_id))
        return {
            "activation": {"active": True},
            "chunk_count": 345,
            "chunk_set_sha256": "e" * 64,
            "compatibility": {"status": "not_requested"},
            "dimension": 384,
            "filters": {"applied_at_query_time": True},
            "generation_id": str(index_id),
            "integrity": {"status": "verified"},
            "lineage": {"parent_generation_id": None},
            "metadata_bytes": 10,
            "model_lock_artifact_id": "model-lock-local",
            "schema_version": "bijux.canon.index.inspection.v1",
            "segments": [{"name": f"segment-{index}"} for index in range(4)],
            "snapshot_artifact_id": "snapshot-lineage-local",
            "text_bytes": 20,
            "vector_bytes": 30,
        }


class _FailingInspectionServices(_RecordingServices):
    def __init__(self, failure: Exception) -> None:
        super().__init__()
        self._failure = failure

    def inspect(self, run_id: str, *, attempt_id: str | None = None):
        del run_id, attempt_id
        raise self._failure


def _write_request(tmp_path: Path, name: str, payload: Mapping[str, object]) -> Path:
    path = tmp_path / f"{name}.json"
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path


def _cli(service: RuntimeApplicationServicesV2 | None, argv: list[str]):
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(["v2", *argv])
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = run_v2_command(args, services=service)
    document = stdout.getvalue() or stderr.getvalue()
    return code, json.loads(document)


@pytest.mark.parametrize(
    ("command", "route"),
    [
        ("ingest", "/api/v2/corpora/prepare"),
        ("index", "/api/v2/indexes/build"),
        ("retrieve", "/api/v2/retrievals"),
        ("ask", "/api/v2/answers"),
        ("research", "/api/v2/research"),
        ("run", "/api/v2/runs"),
    ],
)
def test_create_operations_have_identical_requests_and_responses(
    tmp_path: Path,
    command: str,
    route: str,
) -> None:
    payload = _request_payloads(tmp_path)[command]
    request_path = _write_request(tmp_path, command, payload)
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        [
            command,
            "--request",
            str(request_path),
            "--idempotency-key",
            _IDEMPOTENCY_KEY,
        ],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).post(
        route,
        headers={
            "Bijux-API-Version": "v2",
            "Idempotency-Key": _IDEMPOTENCY_KEY,
        },
        json=payload,
    )

    assert cli_code == 0 and response.status_code == 202
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


@pytest.mark.parametrize(
    ("argv", "operation"),
    [
        (["ingest", "."], "corpus.prepare"),
        (["index", _CORPUS_ID], "index.build"),
        (["search", "steppe ancestry", "--index-id", _INDEX_ID], "retrieve"),
        (["retrieve", "steppe ancestry", "--index-id", _INDEX_ID], "retrieve"),
        (
            [
                "ask",
                "steppe ancestry",
                "--index-id",
                _INDEX_ID,
                "--corpus-id",
                _CORPUS_ID,
            ],
            "ask",
        ),
        (
            [
                "research",
                "steppe ancestry",
                "--index-id",
                _INDEX_ID,
                "--corpus-id",
                _CORPUS_ID,
            ],
            "research",
        ),
        (["run", "steppe ancestry", "--corpus-id", _CORPUS_ID], "run"),
    ],
)
def test_create_operations_accept_ordinary_direct_options(
    argv: list[str], operation: str
) -> None:
    service = _RecordingServices()

    code, payload = _cli(service, argv)

    assert code == 0
    assert payload["schema_version"] == "bijux.runtime.http-job-status.v2"
    name, request, idempotency_key = service.calls[0]
    assert name == operation
    assert str(request.request_id).startswith("request-")
    assert idempotency_key == str(request.request_id)


def test_direct_operation_can_wait_for_a_terminal_result() -> None:
    service = _RecordingServices()

    code, payload = _cli(
        service,
        [
            "search",
            "steppe ancestry",
            "--index-id",
            _INDEX_ID,
            "--wait",
            "--wait-timeout-seconds",
            "2",
        ],
    )

    assert code == 0
    assert payload["status"] == "succeeded"
    assert service.calls[-1] == ("wait", "job_v1_transport_parity", 2.0)


def test_status_follow_waits_with_an_explicit_bound() -> None:
    service = _RecordingServices()

    code, payload = _cli(
        service,
        ["status", "job_v1_transport_parity", "--follow", "--timeout-seconds", "2"],
    )

    assert code == 0
    assert payload["status"] == "succeeded"
    assert service.calls == [("wait", "job_v1_transport_parity", 2.0)]


def test_wait_timeout_is_a_typed_bounded_failure() -> None:
    class _TimeoutServices(_RecordingServices):
        def wait(self, job_id: str, *, timeout_seconds: float | None = None):
            del job_id, timeout_seconds
            raise TimeoutError("operator wait expired")

    code, problem = _cli(
        _TimeoutServices(),
        ["status", "job_v1_transport_parity", "--follow", "--timeout-seconds", "1"],
    )

    assert code == 4
    assert problem["code"] == "operation-failed"
    assert problem["cause"] == "operator wait expired"


def test_process_owned_cli_services_finish_before_return(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingServices()
    closed: list[bool] = []
    monkeypatch.setattr(v2_commands, "_require_services", lambda _: service)
    monkeypatch.setattr(service, "close", lambda: closed.append(True))
    request_path = _write_request(
        tmp_path, "index", _request_payloads(tmp_path)["index"]
    )

    code, _ = _cli(
        None,
        [
            "index",
            "--request",
            str(request_path),
            "--idempotency-key",
            _IDEMPOTENCY_KEY,
        ],
    )

    assert code == 0
    assert closed == [True]


def test_cli_composition_receives_the_one_effective_configuration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingServices()
    captured: list[RuntimeConfiguration] = []
    workspace = tmp_path / "state"
    model = tmp_path / "model"
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(workspace))
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH", str(model))
    monkeypatch.setattr(v2_commands, "_default_application_services", None)
    monkeypatch.setattr(service, "close", lambda: None)

    def compose(*, configuration: RuntimeConfiguration) -> RuntimeApplicationServicesV2:
        captured.append(configuration)
        return service

    monkeypatch.setattr(v2_commands, "compose_runtime_application_services", compose)

    assert v2_commands._require_services(None) is service

    assert len(captured) == 1
    layout = captured[0].require_workspace_layout()
    assert layout.root == workspace.resolve()
    assert layout.model_root == model.resolve()
    assert layout.job_store_path == workspace / "jobs.sqlite"
    v2_commands._close_default_services(service)


def test_process_owned_http_services_close_with_application(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    service = _RecordingServices()
    closed: list[bool] = []
    captured: list[RuntimeConfiguration] = []
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(tmp_path / "state"))
    monkeypatch.setenv(
        "BIJUX_CANON_RUNTIME_EMBEDDING_MODEL_PATH",
        str(tmp_path / "model"),
    )

    def compose(*, configuration: RuntimeConfiguration) -> RuntimeApplicationServicesV2:
        captured.append(configuration)
        return service

    monkeypatch.setattr(v2_app_module, "compose_runtime_application_services", compose)
    monkeypatch.setattr(service, "close", lambda: closed.append(True))

    with TestClient(create_app()) as client:
        response = client.get(
            f"/api/v2/jobs/{_snapshot(JobKind.RUN).job_id}",
            headers={"Bijux-API-Version": "v2"},
        )
        assert response.status_code == 200
        assert closed == []

    assert closed == [True]
    assert len(captured) == 1
    assert captured[0].require_workspace_layout().root == (tmp_path / "state").resolve()


def test_replay_has_identical_request_and_response(tmp_path: Path) -> None:
    payload = {
        "context": _context("replay"),
        "network_policy": "recorded-only",
        "process_id": "transport-parity",
        "provider_allowlist": [],
        "source_attempt_id": _ATTEMPT_ID,
        "timeout_seconds": 30,
    }
    request_path = _write_request(tmp_path, "replay", payload)
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        [
            "replay",
            _RUN_ID,
            "--request",
            str(request_path),
            "--idempotency-key",
            _IDEMPOTENCY_KEY,
        ],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).post(
        f"/api/v2/runs/{_RUN_ID}/replays",
        headers={
            "Bijux-API-Version": "v2",
            "Idempotency-Key": _IDEMPOTENCY_KEY,
        },
        json=payload,
    )

    assert cli_code == 0 and response.status_code == 202
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


def test_replay_accepts_direct_identity_and_wait_options() -> None:
    service = _RecordingServices()

    code, payload = _cli(
        service,
        [
            "replay",
            _RUN_ID,
            "--source-attempt-id",
            _ATTEMPT_ID,
            "--network-policy",
            "recorded-only",
            "--wait",
            "--wait-timeout-seconds",
            "3",
        ],
    )

    assert code == 0
    assert payload["status"] == "succeeded"
    replay_call = service.calls[0]
    assert replay_call[0] == "replay"
    assert replay_call[1].source_attempt_id == _ATTEMPT_ID
    assert replay_call[2].startswith("request-")
    assert service.calls[-1] == ("wait", "job_v1_transport_parity", 3.0)


@pytest.mark.parametrize(
    ("command", "argument", "method", "route"),
    [
        (
            "status",
            "job_v1_transport_parity",
            "get",
            "/api/v2/jobs/job_v1_transport_parity",
        ),
        ("corpus-inspect", _CORPUS_ID, "get", f"/api/v2/corpora/{_CORPUS_ID}"),
        ("index-inspect", _INDEX_ID, "get", f"/api/v2/indexes/{_INDEX_ID}"),
    ],
)
def test_read_operations_have_identical_responses(
    command: str,
    argument: str,
    method: str,
    route: str,
) -> None:
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(cli_service, [command, argument])
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).request(
        method, route, headers={"Bijux-API-Version": "v2"}
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


def test_result_marks_transport_metadata_without_changing_result() -> None:
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(cli_service, ["result", "job_v1_transport_parity"])
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).get(
        "/api/v2/jobs/job_v1_transport_parity/result",
        headers={"Bijux-API-Version": "v2"},
    )
    http_payload = response.json()

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload["schema_version"] == "bijux.runtime.cli-job-result.v2"
    assert http_payload["schema_version"] == "bijux.runtime.http-job-result.v2"
    assert {**cli_payload, "schema_version": None} == {
        **http_payload,
        "schema_version": None,
    }
    assert cli_service.calls == http_service.calls


def test_inspect_pagination_is_identical() -> None:
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        [
            "inspect",
            _RUN_ID,
            "--attempt-id",
            _ATTEMPT_ID,
            "--offset",
            "1",
            "--limit",
            "2",
        ],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).get(
        f"/api/v2/runs/{_RUN_ID}",
        headers={"Bijux-API-Version": "v2"},
        params={"attempt_id": _ATTEMPT_ID, "limit": 2, "offset": 1},
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_payload["page"]["limit"] == 2
    assert cli_payload["page"]["next_offset"] == 3
    assert cli_payload["page"]["offset"] == 1
    assert cli_payload["page"]["next_cursor"]
    assert len(cli_payload["page"]["snapshot_sha256"]) == 64
    assert cli_service.calls == http_service.calls


def test_artifact_payload_pages_have_cli_and_http_parity() -> None:
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        ["artifact-payload", _INDEX_ID, "--offset", "0", "--max-bytes", "4"],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).get(
        f"/api/v2/artifacts/{_INDEX_ID}/payload",
        headers={"Bijux-API-Version": "v2"},
        params={"offset": 0, "max_bytes": 4},
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


def test_inspect_cursor_continuation_is_identical() -> None:
    first_service = _RecordingServices()
    first_code, first_payload = _cli(
        first_service,
        ["inspect", _RUN_ID, "--limit", "2"],
    )
    cursor = first_payload["page"]["next_cursor"]
    assert first_code == 0 and isinstance(cursor, str)

    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        ["inspect", _RUN_ID, "--limit", "2", "--cursor", cursor],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).get(
        f"/api/v2/runs/{_RUN_ID}",
        headers={"Bijux-API-Version": "v2"},
        params={"cursor": cursor, "limit": 2},
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_payload["page"]["offset"] == 2
    assert cli_payload["page"]["next_cursor"] is None
    assert cli_service.calls == http_service.calls


def test_tampered_inspection_cursor_has_equivalent_transport_error() -> None:
    first_code, first_payload = _cli(
        _RecordingServices(),
        ["inspect", _RUN_ID, "--limit", "2"],
    )
    cursor = first_payload["page"]["next_cursor"]
    assert first_code == 0 and isinstance(cursor, str)
    tampered = cursor[:-1] + ("A" if cursor[-1] != "A" else "B")

    cli_code, cli_problem = _cli(
        _RecordingServices(),
        ["inspect", _RUN_ID, "--limit", "2", "--cursor", tampered],
    )
    response = TestClient(create_app(_RecordingServices())).get(
        f"/api/v2/runs/{_RUN_ID}",
        headers={"Bijux-API-Version": "v2"},
        params={"cursor": tampered, "limit": 2},
    )

    assert cli_code == 2 and response.status_code == 400
    assert cli_problem["code"] == response.json()["code"] == "invalid-request"
    assert cli_problem["cause"] == response.json()["cause"]


def test_index_cursor_continuation_is_identical() -> None:
    first_service = _RecordingServices()
    first_code, first_payload = _cli(
        first_service,
        ["index-inspect", _INDEX_ID, "--limit", "2"],
    )
    cursor = first_payload["page"]["next_cursor"]
    assert first_code == 0 and isinstance(cursor, str)

    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        ["index-inspect", _INDEX_ID, "--limit", "2", "--cursor", cursor],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).get(
        f"/api/v2/indexes/{_INDEX_ID}",
        headers={"Bijux-API-Version": "v2"},
        params={"cursor": cursor, "limit": 2},
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_payload["segments"] == [
        {"name": "segment-2"},
        {"name": "segment-3"},
    ]
    assert cli_payload["page"]["offset"] == 2


def test_compare_has_identical_policy_and_response(tmp_path: Path) -> None:
    payload = {
        "baseline_attempt_id": _ATTEMPT_ID,
        "baseline_run_id": _RUN_ID,
        "candidate_attempt_id": "attempt_v1_candidate",
        "candidate_run_id": "run_v1_candidate",
        "context": _context("compare"),
        "dimensions": ["dag", "retrieval", "timing", "policy"],
    }
    request_path = _write_request(tmp_path, "compare", payload)
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service, ["compare", "--request", str(request_path)]
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).post(
        "/api/v2/comparisons",
        headers={"Bijux-API-Version": "v2"},
        json=payload,
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


def test_compare_accepts_direct_attempt_identities() -> None:
    service = _RecordingServices()

    code, payload = _cli(
        service,
        [
            "compare",
            _RUN_ID,
            "run_v1_candidate",
            "--baseline-attempt-id",
            _ATTEMPT_ID,
            "--candidate-attempt-id",
            "attempt_v1_candidate",
            "--dimension",
            "claims",
            "--limit",
            "2",
        ],
    )

    assert code == 0
    assert payload["baseline_run_id"] == _RUN_ID
    assert service.calls[0][0] == "compare"
    assert service.calls[0][1]["policy"].dimensions == (
        v2_commands.ComparisonDimension.CLAIMS,
    )


def test_compare_cursor_continuation_is_identical(tmp_path: Path) -> None:
    payload = {
        "baseline_attempt_id": _ATTEMPT_ID,
        "baseline_run_id": _RUN_ID,
        "candidate_attempt_id": "attempt_v1_candidate",
        "candidate_run_id": "run_v1_candidate",
        "context": _context("compare-page"),
        "dimensions": ["dag", "retrieval", "timing", "policy"],
        "limit": 2,
    }
    first_path = _write_request(tmp_path, "compare-first", payload)
    first_code, first_payload = _cli(
        _RecordingServices(), ["compare", "--request", str(first_path)]
    )
    cursor = first_payload["page"]["next_cursor"]
    assert first_code == 0 and isinstance(cursor, str)
    continued = {**payload, "cursor": cursor}
    continued_path = _write_request(tmp_path, "compare-continued", continued)

    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service, ["compare", "--request", str(continued_path)]
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).post(
        "/api/v2/comparisons",
        headers={"Bijux-API-Version": "v2"},
        json=continued,
    )

    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()
    assert cli_payload["page"]["offset"] == 2
    assert len(cli_payload["differences"]) == 2
    assert cli_payload["page"]["next_cursor"] is None
    assert cli_service.calls == http_service.calls


def test_cancel_has_identical_request_and_response(tmp_path: Path) -> None:
    payload = {"context": _context("cancel"), "reason": "operator request"}
    request_path = _write_request(tmp_path, "cancel", payload)
    cli_service = _RecordingServices()
    cli_code, cli_payload = _cli(
        cli_service,
        [
            "cancel",
            "job_v1_transport_parity",
            "--request",
            str(request_path),
            "--idempotency-key",
            _IDEMPOTENCY_KEY,
        ],
    )
    http_service = _RecordingServices()
    response = TestClient(create_app(http_service)).post(
        "/api/v2/jobs/job_v1_transport_parity/cancellation",
        headers={
            "Bijux-API-Version": "v2",
            "Idempotency-Key": _IDEMPOTENCY_KEY,
        },
        json=payload,
    )

    assert cli_code == 0 and response.status_code == 202
    assert cli_payload == response.json()
    assert cli_service.calls == http_service.calls


def test_cancel_accepts_a_direct_reason() -> None:
    service = _RecordingServices()

    code, payload = _cli(
        service,
        ["cancel", "job_v1_transport_parity", "--reason", "operator shutdown"],
    )

    assert code == 0
    assert payload["status"] == "cancelled"
    assert service.calls == [("cancel", "job_v1_transport_parity")]


def test_backup_and_restore_commands_emit_stable_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    calls: list[object] = []

    class _Protection:
        def __init__(self, configuration: RuntimeConfiguration) -> None:
            calls.append(("configuration", configuration))

        def backup(self, *, backup_id: str, created_at: str | None = None):
            calls.append(("backup", backup_id, created_at))
            return {
                "backup_generation": "/workspace/backups/generations/nightly",
                "manifest": {"backup_id": backup_id},
                "schema_version": "bijux.runtime.workspace-backup-result.v1",
            }

        @staticmethod
        def restore(*, backup_generation: Path, restore_root: Path):
            calls.append(("restore", backup_generation, restore_root))
            return {
                "artifact_count": 2,
                "restore_root": str(restore_root),
                "schema_version": "bijux.runtime.workspace-restore-result.v1",
            }

    monkeypatch.setattr(v2_commands, "RuntimeWorkspaceProtection", _Protection)

    backup_code, backup = _cli(
        None,
        ["backup", "nightly", "--created-at", "2026-08-24T12:00:00+00:00"],
    )
    restore_code, restore = _cli(
        None,
        ["restore", str(tmp_path / "generation"), str(tmp_path / "restored")],
    )

    assert backup_code == restore_code == 0
    assert backup["schema_version"] == "bijux.runtime.workspace-backup-result.v1"
    assert restore["schema_version"] == "bijux.runtime.workspace-restore-result.v1"
    assert calls[1] == ("backup", "nightly", "2026-08-24T12:00:00+00:00")
    assert calls[2] == (
        "restore",
        tmp_path / "generation",
        tmp_path / "restored",
    )


def test_backup_rejects_an_unsafe_identity_as_invalid_request(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", str(tmp_path / "workspace"))

    code, problem = _cli(None, ["backup", "../escape"])

    assert code == 2
    assert problem["code"] == "invalid-request"
    assert problem["cause"].startswith("backup_id must be")
    assert not (tmp_path / "escape").exists()


def test_invalid_body_has_compatible_errors(tmp_path: Path) -> None:
    payload = {"unknown": True}
    request_path = _write_request(tmp_path, "invalid", payload)
    cli_code, cli_problem = _cli(
        _RecordingServices(),
        ["run", "--request", str(request_path), "--idempotency-key", _IDEMPOTENCY_KEY],
    )
    response = TestClient(create_app(_RecordingServices())).post(
        "/api/v2/runs",
        headers={
            "Bijux-API-Version": "v2",
            "Idempotency-Key": _IDEMPOTENCY_KEY,
        },
        json=payload,
    )
    http_problem = response.json()

    assert cli_code == 2 and response.status_code == 400
    assert cli_problem == http_problem


@pytest.mark.parametrize(
    ("failure", "expected_code", "expected_status", "expected_exit"),
    [
        (KeyError("token=private-value at /srv/private/run.json"), "not-found", 404, 4),
        (
            RuntimeError("authorization=private-value at /srv/private/run.json"),
            "operation-failed",
            500,
            4,
        ),
    ],
)
def test_problem_fields_are_identical_across_library_cli_http_and_observability(
    failure: Exception,
    expected_code: str,
    expected_status: int,
    expected_exit: int,
) -> None:
    correlation_id = "correlation-problem-parity"
    cli_code, cli_problem = _cli(
        _FailingInspectionServices(failure),
        ["--correlation-id", correlation_id, "inspect", _RUN_ID],
    )
    response = TestClient(create_app(_FailingInspectionServices(failure))).get(
        f"/api/v2/runs/{_RUN_ID}",
        headers={
            "Bijux-API-Version": "v2",
            "X-Correlation-ID": correlation_id,
        },
    )
    library_fields = runtime_problem_fields(
        runtime_problem(
            RuntimeProblemCode(expected_code),
            correlation_id=correlation_id,
            run_id=_RUN_ID,
            cause=failure,
        )
    )

    assert cli_code == expected_exit and response.status_code == expected_status
    assert cli_problem == response.json() == library_fields
    assert cli_problem["schema_version"] == "bijux.runtime.problem.v2"
    assert cli_problem["correlation_id"] == correlation_id
    assert cli_problem["run_id"] == _RUN_ID
    assert "private-value" not in cli_problem["cause"]
    assert "/srv/private" not in cli_problem["cause"]
    assert "<redacted>" in cli_problem["cause"]
    assert "<path>" in cli_problem["cause"]


def test_unsupported_version_is_a_typed_safe_problem() -> None:
    response = TestClient(create_app(_RecordingServices())).get(
        f"/api/v2/runs/{_RUN_ID}",
        headers={"X-Correlation-ID": "correlation-version"},
    )

    assert response.status_code == 406
    assert response.headers["Bijux-API-Supported-Versions"] == "v2"
    assert response.json() == runtime_problem_fields(
        runtime_problem(
            RuntimeProblemCode.UNSUPPORTED_VERSION,
            correlation_id="correlation-version",
        )
    )


def test_request_context_correlation_survives_missing_composition(
    tmp_path: Path,
) -> None:
    payload = _request_payloads(tmp_path)["run"]
    request_path = _write_request(tmp_path, "missing-composition", payload)
    cli_code, cli_problem = _cli(
        None,
        ["run", "--request", str(request_path), "--idempotency-key", _IDEMPOTENCY_KEY],
    )
    response = TestClient(create_app()).post(
        "/api/v2/runs",
        headers={
            "Bijux-API-Version": "v2",
            "Idempotency-Key": _IDEMPOTENCY_KEY,
        },
        json=payload,
    )

    assert cli_code == 3 and response.status_code == 503
    assert cli_problem == response.json()
    assert cli_problem["correlation_id"] == "correlation-run"


def test_problem_fields_bound_unsafe_identifiers_and_cause() -> None:
    fields = runtime_problem_fields(
        runtime_problem(
            RuntimeProblemCode.OPERATION_FAILED,
            correlation_id="invalid identity",
            run_id="invalid/run",
            cause="password=private " + "x" * 1_000,
        )
    )

    assert fields["correlation_id"] == "correlation-unavailable"
    assert fields["run_id"] == "run-unavailable"
    assert isinstance(fields["cause"], str)
    assert len(fields["cause"]) == 500
    assert "private" not in fields["cause"]
