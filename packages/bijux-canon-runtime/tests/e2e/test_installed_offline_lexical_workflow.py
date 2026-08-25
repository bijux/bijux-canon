# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import pytest

pytestmark = [pytest.mark.e2e, pytest.mark.real_local]

_REPOSITORY_ROOT = Path(__file__).parents[4]
_EXAMPLE = _REPOSITORY_ROOT / "examples" / "ancient-dna-research"


@pytest.mark.timeout(300)
def test_installed_wheels_complete_offline_lexical_workflow(tmp_path: Path) -> None:
    runtime_value = os.environ.get("BIJUX_CANON_RUNTIME_INSTALLED_COMMAND")
    if runtime_value is None:
        pytest.skip("set BIJUX_CANON_RUNTIME_INSTALLED_COMMAND to a fresh-wheel CLI")
    runtime = Path(runtime_value).resolve()
    assert runtime.is_file()

    copied_example = tmp_path / "ancient-dna-research"
    (copied_example / "corpus").mkdir(parents=True)
    shutil.copy2(_EXAMPLE / "offline_lexical_workflow.py", copied_example)
    shutil.copytree(
        _EXAMPLE / "corpus" / "sources", copied_example / "corpus" / "sources"
    )
    command = [
        sys.executable,
        str(copied_example / "offline_lexical_workflow.py"),
        "--runtime-command",
        str(runtime),
        "--workspace",
        str(tmp_path / "runtime-workspace"),
        "--evidence-directory",
        str(tmp_path / "evidence"),
    ]
    environment = dict(os.environ)
    environment.pop("PYTHONPATH", None)
    sandbox = Path("/usr/bin/sandbox-exec")
    if sys.platform == "darwin" and sandbox.is_file():
        command = [
            str(sandbox),
            "-p",
            "(version 1)(allow default)(deny network*)",
            *command,
        ]
        environment["BIJUX_CANON_NETWORK_ISOLATION"] = "os-denied"

    completed = subprocess.run(  # noqa: S603 - explicit installed acceptance CLI
        command,
        cwd=tmp_path,
        env=environment,
        capture_output=True,
        check=False,
        text=True,
        timeout=240,
    )

    assert completed.returncode == 0, completed.stderr
    summary = json.loads(completed.stdout)
    assert summary["result"] == "passed"
    assert summary["profile"] == "offline-lexical"
    assert summary["source_discovery"]["source_count"] == 8
    assert summary["corpus"]["document_count"] == 8
    assert summary["corpus"]["chunk_count"] == summary["index"]["chunk_count"]
    assert summary["corpus"]["rejection_count"] == 0
    assert summary["index"]["backend"] == "sqlite-fts5"
    assert summary["answer_disposition"] == "admitted"
    assert summary["citations"]
    assert all(citation["resolved"] for citation in summary["citations"])
    assert summary["workspace"]["restart_ready"] is True
    assert summary["replay"]["equivalent"] is True
    assert summary["replay"]["exact_artifact_identities"] is True
    lifecycle = summary["lifecycle"]
    assert lifecycle["configuration_comparison"]["equivalent"] is False
    assert lifecycle["configuration_comparison"]["classification"] == "regression"
    assert lifecycle["failed_run"]["status"] == "failed"
    assert lifecycle["failed_run"]["idempotent_retry"] is True
    assert lifecycle["failed_run"]["failure_count"] > 0
    backup_restore = lifecycle["backup_restore"]
    assert backup_restore["artifact_count"] > 0
    assert backup_restore["original_path_unavailable"] is True
    assert backup_restore["failed_job_status"] == "failed"
    assert backup_restore["configuration_mismatch_code"] == "missing-capability"
    assert backup_restore["tampered_restore_code"] == "operation-failed"
    assert backup_restore["restored_replay_attempt_id"]
    assert summary["run"]["bounded_inspection_limit"] == 5
    assert summary["run"]["provenance_status"] == "verified"
    assert all(
        "/packages/" not in path
        for path in summary["installed_environment"]["sys_path"]
    )
    if sys.platform == "darwin":
        assert summary["network_isolation"] == "os-denied"
