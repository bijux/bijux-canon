# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import pytest

from bijux_canon_runtime.application.runtime_configuration import RuntimeConfiguration
from bijux_canon_runtime.application.workspace_initialization import (
    WorkspaceInitializationError,
    WorkspaceInitializationErrorCode,
    WorkspaceInitializationResult,
    WorkspaceInitializationStatus,
)
from bijux_canon_runtime.interfaces.cli.parser import build_parser
from bijux_canon_runtime.interfaces.cli.workspace_commands import (
    EXIT_INITIALIZATION_REFUSED,
    initialize_workspace,
)


def _result(tmp_path: Path) -> WorkspaceInitializationResult:
    return WorkspaceInitializationResult(
        configuration_identity_sha256="c" * 64,
        layout_identity_sha256="l" * 64,
        model_lock_artifact_id="sha256:model",
        status=WorkspaceInitializationStatus.INITIALIZED,
        workspace_id="workspace_v1_identity",
        workspace_root=str(tmp_path / "workspace"),
        workspace_version=2,
    )


def test_parser_exposes_documented_workspace_init() -> None:
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["init", "--workspace", "state", "--model", "models/local", "--json"]
    )

    assert args.command == "init"
    assert args.workspace == "state"
    assert args.model == "models/local"
    assert args.json is True


def test_cli_initializes_offline_lexical_workspace_without_model(
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    workspace = tmp_path / "lexical-workspace"
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["init", "--workspace", str(workspace), "--json"]
    )

    assert initialize_workspace(args) == 0

    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "initialized"
    assert payload["model_lock_artifact_id"].startswith("sha256:")
    assert not (workspace / "models").exists()


def test_cli_entrypoint_routes_workspace_init(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    from bijux_canon_runtime.interfaces.cli import entrypoint

    calls: list[argparse.Namespace] = []

    def initialize(args: argparse.Namespace) -> int:
        calls.append(args)
        return 0

    monkeypatch.setattr(entrypoint, "initialize_workspace", initialize)
    monkeypatch.setattr(
        sys,
        "argv",
        ["bijux-canon-runtime", "init", "--workspace", "state", "--model", "model"],
    )

    with pytest.raises(SystemExit) as raised:
        entrypoint.main()

    assert raised.value.code == 0
    assert len(calls) == 1


def test_json_init_emits_one_stable_success_document(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    captured: list[RuntimeConfiguration] = []
    expected = _result(tmp_path)

    def initialize(
        configuration: RuntimeConfiguration,
    ) -> WorkspaceInitializationResult:
        captured.append(configuration)
        return expected

    monkeypatch.setattr(
        "bijux_canon_runtime.interfaces.cli.workspace_commands."
        "initialize_runtime_workspace",
        initialize,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "init",
            "--workspace",
            str(tmp_path / "workspace"),
            "--model",
            str(tmp_path / "model"),
            "--json",
        ]
    )

    exit_code = initialize_workspace(args)

    assert exit_code == 0
    assert json.loads(capsys.readouterr().out) == expected.record()
    layout = captured[0].require_workspace_layout()
    assert layout.root == (tmp_path / "workspace").resolve()
    assert layout.model_root == (tmp_path / "model").resolve()


def test_cli_resolves_relative_model_from_the_calling_directory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: list[RuntimeConfiguration] = []
    expected = _result(tmp_path)
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(
        "bijux_canon_runtime.interfaces.cli.workspace_commands."
        "initialize_runtime_workspace",
        lambda configuration: captured.append(configuration) or expected,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["init", "--workspace", "workspace", "--model", "model", "--json"]
    )

    assert initialize_workspace(args) == 0
    layout = captured[0].require_workspace_layout()
    assert layout.root == tmp_path / "workspace"
    assert layout.model_root == tmp_path / "model"


def test_human_init_identifies_outcome_workspace_and_identities(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = _result(tmp_path)
    monkeypatch.setattr(
        "bijux_canon_runtime.interfaces.cli.workspace_commands."
        "initialize_runtime_workspace",
        lambda _configuration: expected,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["init", "--workspace", "state", "--model", "model"]
    )

    assert initialize_workspace(args) == 0

    output = capsys.readouterr().out
    assert "Workspace initialized:" in output
    assert expected.workspace_id in output
    assert expected.model_lock_artifact_id in output


def test_human_migration_identifies_ordered_change_and_rollback_backup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    expected = WorkspaceInitializationResult(
        configuration_identity_sha256="c" * 64,
        layout_identity_sha256="l" * 64,
        model_lock_artifact_id="sha256:model",
        status=WorkspaceInitializationStatus.MIGRATED,
        workspace_id="workspace_v1_migrated",
        workspace_root=str(tmp_path / "workspace"),
        workspace_version=2,
        applied_migration_ids=("sha256:" + "a" * 64,),
        rollback_backup_path=str(tmp_path / "workspace/backups/migration"),
    )
    monkeypatch.setattr(
        "bijux_canon_runtime.interfaces.cli.workspace_commands."
        "initialize_runtime_workspace",
        lambda _configuration: expected,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        ["init", "--workspace", "state", "--model", "model"]
    )

    assert initialize_workspace(args) == 0
    output = capsys.readouterr().out
    assert "Workspace migrated:" in output
    assert expected.applied_migration_ids[0] in output
    assert expected.rollback_backup_path in output


def test_json_refusal_is_typed_and_actionable(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    def refuse(_configuration: object) -> None:
        raise WorkspaceInitializationError(
            WorkspaceInitializationErrorCode.PARTIAL_WORKSPACE,
            "workspace exists without a valid manifest",
            "restore a backup",
        )

    monkeypatch.setattr(
        "bijux_canon_runtime.interfaces.cli.workspace_commands."
        "initialize_runtime_workspace",
        refuse,
    )
    args = build_parser(prog_name="bijux-canon-runtime").parse_args(
        [
            "init",
            "--workspace",
            str(tmp_path / "workspace"),
            "--model",
            str(tmp_path / "model"),
            "--json",
        ]
    )

    assert initialize_workspace(args) == EXIT_INITIALIZATION_REFUSED

    captured = capsys.readouterr()
    assert captured.out == ""
    assert json.loads(captured.err) == {
        "code": "partial_workspace",
        "detail": "workspace exists without a valid manifest",
        "remediation": "restore a backup",
        "schema_version": "bijux.runtime.workspace-initialization-error.v1",
        "status": "refused",
    }
