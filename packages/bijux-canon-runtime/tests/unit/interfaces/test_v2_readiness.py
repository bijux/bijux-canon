from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.readiness import (
    ReadinessReason,
    RuntimeReadinessService,
    runtime_liveness,
)
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import (
    EXIT_NOT_READY,
    run_v2_command,
)


def _configuration(tmp_path: Path, **overrides: object):
    index_root = tmp_path / "index"
    index_root.mkdir(exist_ok=True)
    return resolve_runtime_configuration(
        explicit={
            "database_path": tmp_path / "runtime.duckdb",
            "retrieval_index_path": index_root,
            "working_root": tmp_path / "runtime-state",
            "offline": True,
            **overrides,
        }
    )


def _verified_index(_path: Path):
    class Service:
        def verify(self):
            return SimpleNamespace(
                activation=SimpleNamespace(
                    active=True,
                    active_generation_id="sha256:" + "a" * 64,
                ),
                dimension=384,
                generation_id="sha256:" + "a" * 64,
                integrity=SimpleNamespace(status="verified"),
                model_lock_artifact_id="sha256:" + "b" * 64,
            )

    return Service()


def _cli(
    command: str,
    *,
    readiness: RuntimeReadinessService | None = None,
) -> tuple[int, dict[str, object]]:
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", command]
    )
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = run_v2_command(
            args,
            services=None,
            readiness_service=readiness,
        )
    return code, json.loads(stdout.getvalue() or stderr.getvalue())


def test_liveness_performs_no_dependency_checks(monkeypatch: pytest.MonkeyPatch) -> None:
    readiness_module = __import__(
        "bijux_canon_runtime.application.readiness",
        fromlist=["readiness"],
    )

    def fail(*_args: object, **_kwargs: object):
        raise AssertionError("liveness must not touch a dependency")

    monkeypatch.setattr(readiness_module, "DuckDBExecutionStore", fail)
    monkeypatch.setattr(readiness_module, "IndexService", fail)

    report = runtime_liveness()
    cli_code, cli_payload = _cli("live")
    response = TestClient(create_app()).get(
        "/api/v2/live",
        headers={"Bijux-API-Version": "v2"},
    )

    assert report.live and report.status == "ok"
    assert cli_code == 0 and response.status_code == 200
    assert cli_payload == response.json()


def test_deep_readiness_passes_every_required_check(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_module = __import__(
        "bijux_canon_runtime.application.readiness",
        fromlist=["readiness"],
    )
    monkeypatch.setattr(readiness_module, "IndexService", _verified_index)
    service = RuntimeReadinessService(_configuration(tmp_path))

    report = service.evaluate()
    restarted = RuntimeReadinessService(_configuration(tmp_path)).evaluate()

    assert report.ready and report.status == "ready"
    assert restarted == report
    assert len(report.checks) == 6
    assert all(check.ready for check in report.checks)
    assert report.reasons == ()
    assert not tuple(tmp_path.rglob(".readiness.*"))


def test_readiness_retains_all_safe_degraded_reasons() -> None:
    service = RuntimeReadinessService(resolve_runtime_configuration())

    report = service.evaluate()

    assert not report.ready and report.status == "degraded"
    assert report.reasons == (
        ReadinessReason.DATABASE_NOT_CONFIGURED,
        ReadinessReason.ARTIFACT_STORE_NOT_CONFIGURED,
        ReadinessReason.INDEX_NOT_CONFIGURED,
        ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,
        ReadinessReason.STATE_NOT_WRITABLE,
    )
    assert all(check.reason is not None for check in report.checks if not check.ready)


def test_online_readiness_requires_only_the_referenced_provider_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_module = __import__(
        "bijux_canon_runtime.application.readiness",
        fromlist=["readiness"],
    )
    monkeypatch.setattr(readiness_module, "IndexService", _verified_index)
    configuration = _configuration(
        tmp_path,
        offline=False,
        provider_api_key_ref="RESEARCH_PROVIDER_KEY",
    )

    missing = RuntimeReadinessService(configuration, environment={}).evaluate()
    configured = RuntimeReadinessService(
        configuration,
        environment={"RESEARCH_PROVIDER_KEY": "not-returned-by-readiness"},
    ).evaluate()

    assert ReadinessReason.PROVIDER_CONFIGURATION_UNAVAILABLE in missing.reasons
    assert configured.ready
    assert "not-returned-by-readiness" not in repr(configured)


def test_readiness_reports_writability_failure_without_losing_other_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_module = __import__(
        "bijux_canon_runtime.application.readiness",
        fromlist=["readiness"],
    )
    monkeypatch.setattr(readiness_module, "IndexService", _verified_index)

    def reject_write(_root: Path) -> None:
        raise OSError("not writable")

    monkeypatch.setattr(RuntimeReadinessService, "_write_probe", staticmethod(reject_write))
    report = RuntimeReadinessService(_configuration(tmp_path)).evaluate()

    assert report.reasons == (ReadinessReason.STATE_NOT_WRITABLE,)
    assert sum(check.ready for check in report.checks) == 5
    assert "not writable" not in repr(report)


def test_cli_and_http_return_the_same_ready_and_degraded_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    readiness_module = __import__(
        "bijux_canon_runtime.application.readiness",
        fromlist=["readiness"],
    )
    monkeypatch.setattr(readiness_module, "IndexService", _verified_index)
    ready_service = RuntimeReadinessService(_configuration(tmp_path))
    ready_code, ready_cli = _cli("ready", readiness=ready_service)
    ready_http = TestClient(create_app(readiness=ready_service)).get(
        "/api/v2/ready",
        headers={"Bijux-API-Version": "v2"},
    )

    degraded_service = RuntimeReadinessService(resolve_runtime_configuration())
    degraded_code, degraded_cli = _cli("ready", readiness=degraded_service)
    degraded_http = TestClient(create_app(readiness=degraded_service)).get(
        "/api/v2/ready",
        headers={"Bijux-API-Version": "v2"},
    )

    assert ready_code == 0 and ready_http.status_code == 200
    assert ready_cli == ready_http.json()
    assert degraded_code == EXIT_NOT_READY and degraded_http.status_code == 503
    assert degraded_cli == degraded_http.json()
