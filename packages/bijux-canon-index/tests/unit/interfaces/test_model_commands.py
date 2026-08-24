# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from bijux_canon_index.interfaces.cli import app as cli_app
from bijux_canon_index.interfaces.cli import model_commands


class _Record:
    def record(self) -> dict[str, object]:
        return {
            "dimension": 384,
            "offline_reuse": True,
            "record_id": "sha256:validated",
            "validation_result": "passed",
        }


def test_installed_model_commands_emit_validation_records(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[tuple[str, Path, str]] = []
    monkeypatch.setattr(
        model_commands,
        "acquire_model",
        lambda root, *, profile_id: (
            calls.append(("acquire", root, profile_id)) or _Record()
        ),
    )
    monkeypatch.setattr(
        model_commands,
        "register_existing_model",
        lambda root, *, profile_id: (
            calls.append(("register", root, profile_id)) or _Record()
        ),
    )
    monkeypatch.setattr(
        model_commands,
        "validate_model",
        lambda root, *, profile_id: (
            calls.append(("validate", root, profile_id)) or _Record()
        ),
    )
    runner = CliRunner()

    results = (
        runner.invoke(cli_app.app, ["model", "acquire", "--cache-root", str(tmp_path)]),
        runner.invoke(
            cli_app.app, ["model", "register", "--model-root", str(tmp_path)]
        ),
        runner.invoke(
            cli_app.app, ["model", "validate", "--model-root", str(tmp_path)]
        ),
    )

    assert all(result.exit_code == 0 for result in results)
    assert all(json.loads(result.stdout)["offline_reuse"] for result in results)
    assert [call[0] for call in calls] == ["acquire", "register", "validate"]
    assert all(call[2] == "local-minilm-384" for call in calls)


def test_model_command_returns_stable_error_exit(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        model_commands,
        "validate_model",
        lambda *_args, **_kwargs: (_ for _ in ()).throw(
            model_commands.ModelLifecycleError("model validation failed: corrupt")
        ),
    )

    result = CliRunner().invoke(
        cli_app.app,
        ["model", "validate", "--model-root", str(tmp_path)],
    )

    assert result.exit_code == 1
    assert "model validation failed: corrupt" in result.stderr
