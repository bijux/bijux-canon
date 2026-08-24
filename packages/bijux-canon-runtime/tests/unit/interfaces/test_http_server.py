# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import importlib.util
import os
from pathlib import Path
import tomllib

import pytest

from bijux_canon_runtime.api.v2 import create_app
from bijux_canon_runtime.interfaces.http.server import ServerSettings, main

pytestmark = pytest.mark.unit


def test_installed_server_uses_loopback_safe_defaults() -> None:
    observed: list[ServerSettings] = []

    assert main([], runner=observed.append) == 0

    assert observed == [
        ServerSettings(
            host="127.0.0.1",
            port=8000,
            log_level="info",
            access_log=True,
        )
    ]


def test_server_resolves_workspace_and_process_options(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    observed: list[ServerSettings] = []
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("BIJUX_CANON_RUNTIME_WORKING_ROOT", raising=False)

    assert (
        main(
            [
                "--workspace",
                "workspace",
                "--host",
                "0.0.0.0",
                "--port",
                "8123",
                "--log-level",
                "warning",
                "--no-access-log",
            ],
            runner=observed.append,
        )
        == 0
    )

    assert observed == [
        ServerSettings(
            host="0.0.0.0",
            port=8123,
            log_level="warning",
            access_log=False,
        )
    ]
    assert Path(os.environ["BIJUX_CANON_RUNTIME_WORKING_ROOT"]) == (
        tmp_path / "workspace"
    ).resolve()


@pytest.mark.parametrize("value", ("0", "65536"))
def test_server_rejects_invalid_ports(value: str) -> None:
    with pytest.raises(SystemExit, match="2"):
        main(["--port", value], runner=lambda _: None)


def test_server_reports_missing_api_extra(capsys: pytest.CaptureFixture[str]) -> None:
    def unavailable(_: ServerSettings) -> None:
        raise RuntimeError(
            "HTTP dependencies are unavailable; install bijux-canon-runtime[api]"
        )

    assert main([], runner=unavailable) == 2
    assert capsys.readouterr().err == (
        "bijux-canon-runtime-server: HTTP dependencies are unavailable; install "
        "bijux-canon-runtime[api]\n"
    )


def test_runtime_distribution_declares_installed_server_entrypoint() -> None:
    package_root = Path(__file__).resolve().parents[3]
    project = tomllib.loads((package_root / "pyproject.toml").read_text("utf-8"))

    assert project["project"]["scripts"]["bijux-canon-runtime-server"] == (
        "bijux_canon_runtime.interfaces.http.server:main"
    )
    assert importlib.util.find_spec(
        "bijux_canon_runtime.interfaces.http.server"
    ) is not None


def test_v2_openapi_declares_unauthenticated_transport_posture() -> None:
    schema = create_app().openapi()

    assert schema["security"] == []
    assert schema["servers"] == [{"url": "/"}]
    assert "securitySchemes" not in schema.get("components", {})
    missing_capability = schema["paths"]["/api/v2/runs"]["post"]["responses"][
        "503"
    ]
    assert "application/problem+json" in missing_capability["content"]
