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
from bijux_canon_index.application import model_lifecycle
from bijux_canon_index.application.model_lifecycle import validate_model
from bijux_canon_index.infra.embeddings.model_cache import materialize_model
from bijux_canon_runtime import discover_runtime_capabilities
from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.application.capability_discovery import (
    RuntimeCapabilityDiscoveryService,
)
from bijux_canon_runtime.application.runtime_configuration import (
    RuntimeConfiguration,
    resolve_runtime_configuration,
)
from bijux_canon_runtime.application.workspace_initialization import (
    initialize_runtime_workspace,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.v2_commands import run_v2_command


class _Encoded(list[list[float]]):
    dtype = "float32"


class _Model:
    def encode(self, _texts: list[str], **_options: object) -> _Encoded:
        value = 1.0 / (LOCAL_MINILM_PROFILE.dimension**0.5)
        return _Encoded([[value] * LOCAL_MINILM_PROFILE.dimension])


def _materialized_model(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> Path:
    cache_root = tmp_path / "model-cache"
    metadata: dict[str, object] = {
        "sha": LOCAL_MINILM_PROFILE.revision,
        "cardData": {"license": "apache-2.0"},
        "siblings": [
            {"rfilename": path} for path in LOCAL_MINILM_PROFILE.required_artifacts
        ],
    }

    def fetch_artifact(_url: str, destination: Path) -> None:
        destination.write_bytes(b"valid")

    lock = materialize_model(
        LOCAL_MINILM_PROFILE,
        cache_root,
        library_versions=(("sentence-transformers", "5.1.0"),),
        metadata_fetcher=lambda _url: metadata,
        artifact_fetcher=fetch_artifact,
    )
    root = cache_root / LOCAL_MINILM_PROFILE.profile_id / LOCAL_MINILM_PROFILE.revision
    monkeypatch.setattr(model_lifecycle, "_PINNED_ARTIFACTS", lock.artifacts)
    validate_model(root, loader=lambda *_: _Model())
    return root


def _service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    secret: str,
) -> tuple[RuntimeCapabilityDiscoveryService, RuntimeConfiguration]:
    model = _materialized_model(tmp_path, monkeypatch)
    configuration = resolve_runtime_configuration(
        explicit={
            "embedding_model_path": model,
            "offline": False,
            "provider_api_key_ref": "RESEARCH_PROVIDER_KEY",
            "working_root": tmp_path / "workspace",
        }
    )
    initialize_runtime_workspace(configuration)
    lock_id = initialize_runtime_workspace(configuration).model_lock_artifact_id
    configuration.require_workspace_layout().active_generation_path.write_text(
        "{}",
        encoding="utf-8",
    )

    class VerifiedIndex:
        def __init__(self, _path: Path) -> None:
            pass

        def verify(self):
            return SimpleNamespace(
                activation=SimpleNamespace(
                    active=True,
                    active_generation_id="sha256:" + "a" * 64,
                ),
                chunk_count=493,
                chunk_set_sha256="b" * 64,
                dimension=LOCAL_MINILM_PROFILE.dimension,
                generation_id="sha256:" + "a" * 64,
                integrity=SimpleNamespace(status="verified"),
                model_lock_artifact_id=lock_id,
                snapshot_artifact_id="sha256:" + "c" * 64,
            )

    monkeypatch.setattr(
        "bijux_canon_runtime.application.capability_discovery.IndexService",
        VerifiedIndex,
    )
    monkeypatch.setattr(
        "bijux_canon_runtime.application.readiness.IndexService",
        VerifiedIndex,
    )
    return (
        RuntimeCapabilityDiscoveryService(
            configuration,
            environment={"RESEARCH_PROVIDER_KEY": secret},
        ),
        configuration,
    )


@pytest.mark.parametrize(
    "secret",
    [
        "sk-live-secret-value",
        "Bearer embedded-credential-token",
        "unicode-secret-åäö",
    ],
)
def test_python_discovery_reports_real_support_without_secret_values(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    secret: str,
) -> None:
    service, configuration = _service(tmp_path, monkeypatch, secret=secret)

    report = service.inspect()
    public_report = discover_runtime_capabilities(
        configuration,
        environment={"RESEARCH_PROVIDER_KEY": secret},
    )
    payload = json.dumps(report.record(), default=str, sort_keys=True)

    assert public_report == report
    assert secret not in payload
    assert report.provider_credential_available
    assert report.configuration["provider_api_key_ref"] == "RESEARCH_PROVIDER_KEY"
    assert report.configuration["origins"]["working_root"] == "explicit"
    assert report.workspace.status == "initialized"
    assert report.model.status == "verified"
    assert report.model.validation_record_id is not None
    assert report.model.artifact_set_digest is not None
    assert report.model.license_pointer is not None
    assert report.model.compatibility_status == "compatible"
    assert report.model.validation_result == "passed"
    assert report.model.offline_reuse
    assert report.index.status == "active"
    assert report.index.chunk_count == 493
    assert [item.format_id for item in report.parsers] == [
        "jats",
        "pdf-digital",
        "html",
        "markdown",
        "text",
        "docx",
        "ocr-required",
    ]
    assert report.parsers[-1].disposition == "typed_refusal"
    assert [item.provider_id for item in report.providers] == [
        "credential-free",
        "local-recorded",
    ]
    assert len(report.readiness) == 7
    assert all(item.ready for item in report.readiness)


def test_cli_http_and_human_discovery_share_one_report(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "never-return-this-provider-token"
    service, _configuration = _service(tmp_path, monkeypatch, secret=secret)
    parser = build_parser(prog_name="bijux-canon-runtime")
    json_args = parser.parse_args(["v2", "capabilities"])
    human_args = parser.parse_args(["v2", "capabilities", "--human"])

    json_stdout, stderr = StringIO(), StringIO()
    with redirect_stdout(json_stdout), redirect_stderr(stderr):
        json_code = run_v2_command(
            json_args,
            services=None,
            capability_discovery_service=service,
        )
    human_stdout = StringIO()
    with redirect_stdout(human_stdout), redirect_stderr(stderr):
        human_code = run_v2_command(
            human_args,
            services=None,
            capability_discovery_service=service,
        )
    response = TestClient(create_app(discovery=service)).get(
        "/api/v2/capabilities",
        headers={"Bijux-API-Version": "v2"},
    )
    payload = json.loads(json_stdout.getvalue())
    human = human_stdout.getvalue()

    assert json_code == human_code == 0
    assert response.status_code == 200
    assert payload == response.json() == service.inspect().record()
    assert payload["configuration"]["identity_sha256"] in human
    assert payload["workspace"]["workspace_id"] in human
    assert payload["model"]["model_lock_artifact_id"] in human
    assert payload["index"]["generation_id"] in human
    for parser_capability in payload["parsers"]:
        assert (
            f"{parser_capability['format_id']}={parser_capability['disposition']}"
            in human
        )
    for provider in payload["providers"]:
        assert provider["provider_id"] in human
    for readiness in payload["readiness"]:
        assert f"{readiness['capability']}={readiness['status']}" in human
    assert secret not in human + json_stdout.getvalue() + response.text


def test_unconfigured_discovery_is_non_mutating_and_complete(tmp_path: Path) -> None:
    configuration = resolve_runtime_configuration(
        explicit={"working_root": tmp_path / "absent"}
    )

    report = RuntimeCapabilityDiscoveryService(configuration, environment={}).inspect()

    assert report.workspace.status == "unavailable"
    assert report.model.status == "unavailable"
    assert report.index.status == "unavailable"
    assert not all(item.ready for item in report.readiness)
    assert not (tmp_path / "absent").exists()
