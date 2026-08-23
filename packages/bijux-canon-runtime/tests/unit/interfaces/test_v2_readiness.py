# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from io import StringIO
import json
from pathlib import Path
from types import SimpleNamespace

from fastapi.testclient import TestClient
import pytest

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE
from bijux_canon_index.infra.embeddings.model_cache import (
    load_model_lock,
    materialize_model,
)
from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.readiness import (
    ReadinessCapability,
    ReadinessReason,
    RuntimeReadinessService,
    runtime_liveness,
    runtime_store_is_ready,
)
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    initialize_runtime_workspace,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import (
    EXIT_NOT_READY,
    run_v2_command,
)


def _materialized_model(tmp_path: Path) -> Path:
    cache_root = tmp_path / "model-cache"
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    materialize_model(
        LOCAL_MINILM_PROFILE,
        cache_root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch,
    )
    return cache_root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision


def _initialized_configuration(
    tmp_path: Path,
    **overrides: object,
) -> RuntimeConfiguration:
    model = _materialized_model(tmp_path)
    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "working_root": tmp_path / "runtime-state",
            **overrides,
        }
    )
    initialize_runtime_workspace(configuration)
    return configuration


def _verified_index(model_lock_id: str, dimension: int):
    class Service:
        def __init__(self, _path: Path) -> None:
            pass

        def verify(self):
            return SimpleNamespace(
                activation=SimpleNamespace(
                    active=True,
                    active_generation_id="sha256:" + "a" * 64,
                ),
                dimension=dimension,
                generation_id="sha256:" + "a" * 64,
                integrity=SimpleNamespace(status="verified"),
                model_lock_artifact_id=model_lock_id,
            )

    return Service


def _patch_verified_index(
    configuration: RuntimeConfiguration,
    monkeypatch: pytest.MonkeyPatch,
    *,
    model_lock_id: str | None = None,
) -> None:
    layout = configuration.require_workspace_layout()
    lock = load_model_lock(layout.model_lock_path)
    monkeypatch.setattr(
        "bijux_canon_runtime.application.readiness.IndexService",
        _verified_index(model_lock_id or lock.lock_id, lock.profile.dimension),
    )


def _cli(
    capability: ReadinessCapability,
    *,
    readiness: RuntimeReadinessService,
) -> tuple[int, dict[str, object]]:
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["v2", "ready", "--operation", capability.value]
    )
    stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(stdout), redirect_stderr(stderr):
        code = run_v2_command(
            args,
            services=None,
            readiness_service=readiness,
        )
    return code, json.loads(stdout.getvalue() or stderr.getvalue())


def test_liveness_performs_no_dependency_checks(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fail(*_args: object, **_kwargs: object):
        raise AssertionError("liveness must not touch a dependency")

    monkeypatch.setattr(
        "bijux_canon_runtime.application.readiness.DuckDBExecutionStore", fail
    )
    monkeypatch.setattr("bijux_canon_runtime.application.readiness.IndexService", fail)

    report = runtime_liveness()
    response = TestClient(create_app()).get(
        "/api/v2/live",
        headers={"Bijux-API-Version": "v2"},
    )

    assert report.live and report.status == "ok"
    assert response.status_code == 200
    assert response.json()["schema_version"] == "bijux.runtime.liveness.v1"


def test_initialized_and_ingest_readiness_need_no_active_index(
    tmp_path: Path,
) -> None:
    configuration = _initialized_configuration(tmp_path)
    service = RuntimeReadinessService(configuration)

    initialized = service.evaluate()
    ingest = service.evaluate(ReadinessCapability.INGEST)

    assert initialized.ready and ingest.ready
    assert initialized.capability is ReadinessCapability.INITIALIZED
    assert len(initialized.checks) == 4
    assert initialized == RuntimeReadinessService(configuration).evaluate()
    assert not tuple(tmp_path.rglob(".readiness.*"))


def test_ingest_remains_ready_when_the_optional_model_is_missing(
    tmp_path: Path,
) -> None:
    configuration = _initialized_configuration(tmp_path)
    layout = configuration.require_workspace_layout()
    lock = load_model_lock(layout.model_lock_path)
    (layout.model_root / lock.artifacts[0].path).unlink()
    service = RuntimeReadinessService(configuration)

    ingest = service.evaluate(ReadinessCapability.INGEST)
    index = service.evaluate(ReadinessCapability.INDEX)

    assert ingest.ready
    assert not index.ready
    assert index.reasons == (ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,)


def test_retrieval_requires_an_active_generation_bound_to_the_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = _initialized_configuration(tmp_path)
    service = RuntimeReadinessService(configuration)

    missing = service.evaluate(ReadinessCapability.RETRIEVE)
    _patch_verified_index(configuration, monkeypatch)
    ready = service.evaluate(ReadinessCapability.RETRIEVE)

    assert missing.reasons == (ReadinessReason.ACTIVE_GENERATION_UNAVAILABLE,)
    assert ready.ready


def test_retrieval_rejects_active_generation_from_another_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = _initialized_configuration(tmp_path)
    _patch_verified_index(
        configuration,
        monkeypatch,
        model_lock_id="sha256:" + "f" * 64,
    )

    report = RuntimeReadinessService(configuration).evaluate(
        ReadinessCapability.RETRIEVE
    )

    assert report.reasons == (ReadinessReason.MODEL_CONFIGURATION_UNAVAILABLE,)


def test_optional_provider_is_required_only_for_selected_online_answering(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = _initialized_configuration(
        tmp_path,
        offline=False,
        provider_api_key_ref="RESEARCH_PROVIDER_KEY",
    )
    _patch_verified_index(configuration, monkeypatch)

    missing = RuntimeReadinessService(configuration, environment={})
    configured = RuntimeReadinessService(
        configuration,
        environment={"RESEARCH_PROVIDER_KEY": "not-returned-by-readiness"},
    )

    assert missing.evaluate(ReadinessCapability.INGEST).ready
    assert missing.evaluate(ReadinessCapability.ASK).reasons == (
        ReadinessReason.PROVIDER_CONFIGURATION_UNAVAILABLE,
    )
    assert configured.evaluate(ReadinessCapability.ASK).ready
    assert "not-returned-by-readiness" not in repr(
        configured.evaluate(ReadinessCapability.ASK)
    )


def test_uninitialized_readiness_is_non_mutating_and_actionable(
    tmp_path: Path,
) -> None:
    workspace = tmp_path / "runtime-state"
    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": tmp_path / "missing-model",
            "working_root": workspace,
        }
    )

    report = RuntimeReadinessService(configuration).evaluate(ReadinessCapability.RUN)

    assert not report.ready
    assert ReadinessReason.WORKSPACE_INVALID in report.reasons
    assert ReadinessReason.SCHEMA_UNAVAILABLE in report.reasons
    assert ReadinessReason.ARTIFACT_STORE_UNAVAILABLE in report.reasons
    assert ReadinessReason.STATE_NOT_WRITABLE in report.reasons
    assert not workspace.exists()


def test_absent_workspace_configuration_retains_all_required_reasons() -> None:
    report = RuntimeReadinessService(resolve_runtime_configuration()).evaluate()

    assert report.reasons == (
        ReadinessReason.WORKSPACE_NOT_CONFIGURED,
        ReadinessReason.DATABASE_NOT_CONFIGURED,
        ReadinessReason.ARTIFACT_STORE_NOT_CONFIGURED,
        ReadinessReason.STATE_NOT_WRITABLE,
    )


def test_partial_and_corrupt_workspaces_are_not_reported_initialized(
    tmp_path: Path,
) -> None:
    model = _materialized_model(tmp_path)
    partial_root = tmp_path / "partial"
    partial_root.mkdir()
    partial = resolve_runtime_configuration(
        explicit={"embedding_model_path": model, "working_root": partial_root}
    )
    partial_report = RuntimeReadinessService(partial).evaluate()

    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "working_root": tmp_path / "initialized",
        }
    )
    initialize_runtime_workspace(configuration)
    layout = configuration.require_workspace_layout()
    layout.database_path.write_bytes(b"corrupt")
    corrupt_report = RuntimeReadinessService(configuration).evaluate()

    assert ReadinessReason.WORKSPACE_INVALID in partial_report.reasons
    assert ReadinessReason.WORKSPACE_INVALID in corrupt_report.reasons
    assert ReadinessReason.SCHEMA_UNAVAILABLE in corrupt_report.reasons


def test_readiness_reports_writability_failure_without_losing_safe_checks(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = _initialized_configuration(tmp_path)

    def reject_write(_root: Path) -> None:
        raise OSError("not writable")

    monkeypatch.setattr(
        RuntimeReadinessService,
        "_write_probe",
        staticmethod(reject_write),
    )
    report = RuntimeReadinessService(configuration).evaluate()

    assert report.reasons == (ReadinessReason.STATE_NOT_WRITABLE,)
    assert sum(check.ready for check in report.checks) == 3
    assert "not writable" not in repr(report)


def test_cli_and_http_return_identical_capability_reports(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    configuration = _initialized_configuration(tmp_path)
    _patch_verified_index(configuration, monkeypatch)
    service = RuntimeReadinessService(configuration)

    ready_code, ready_cli = _cli(ReadinessCapability.RETRIEVE, readiness=service)
    ready_http = TestClient(create_app(readiness=service)).get(
        "/api/v2/ready",
        params={"operation": "retrieve"},
        headers={"Bijux-API-Version": "v2"},
    )
    degraded_service = RuntimeReadinessService(resolve_runtime_configuration())
    degraded_code, degraded_cli = _cli(
        ReadinessCapability.INGEST,
        readiness=degraded_service,
    )
    degraded_http = TestClient(create_app(readiness=degraded_service)).get(
        "/api/v2/ready",
        params={"operation": "ingest"},
        headers={"Bijux-API-Version": "v2"},
    )

    assert ready_code == 0 and ready_http.status_code == 200
    assert ready_cli == ready_http.json()
    assert degraded_code == EXIT_NOT_READY and degraded_http.status_code == 503
    assert degraded_cli == degraded_http.json()


def test_store_probe_does_not_create_a_missing_database(tmp_path: Path) -> None:
    database = tmp_path / "missing.duckdb"

    assert not runtime_store_is_ready(database)
    assert not database.exists()
