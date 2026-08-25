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
_EXAMPLE = _REPOSITORY_ROOT / "examples" / "urban-heat-research"


@pytest.mark.timeout(300)
def test_installed_wheels_generalize_to_independent_corpus(tmp_path: Path) -> None:
    runtime_value = os.environ.get("BIJUX_CANON_RUNTIME_INSTALLED_COMMAND")
    if runtime_value is None:
        pytest.skip("set BIJUX_CANON_RUNTIME_INSTALLED_COMMAND to a fresh-wheel CLI")
    runtime = Path(runtime_value).resolve()
    assert runtime.is_file()

    copied_example = tmp_path / "urban-heat-research"
    shutil.copytree(_EXAMPLE, copied_example)
    command = [
        sys.executable,
        str(copied_example / "offline_generalization_workflow.py"),
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
    assert summary["corpus"]["document_count"] == 4
    assert summary["corpus"]["format_count"] == 4
    assert summary["corpus"]["rejection_count"] == 0
    assert summary["index"]["backend"] == "sqlite-fts5"
    assert {case["disposition"] for case in summary["cases"]} == {
        "admitted",
        "abstained",
    }
    assert all(case["unsupported_material_claims"] == 0 for case in summary["cases"])
    unsupported = next(
        case for case in summary["cases"] if case["disposition"] == "abstained"
    )
    assert unsupported["claim_count"] == unsupported["citation_count"] == 0
    assert summary["research"]["distinct_evidence_need_count"] >= 2
    assert summary["research"]["candidate_classification_count"] >= 1
    assert summary["research"]["citation_count"] >= 1
    assert summary["research"]["unsupported_material_claims"] == 0
    assert all(
        "/packages/" not in path
        for path in summary["installed_environment"]["sys_path"]
    )
    if sys.platform == "darwin":
        assert summary["network_isolation"] == "os-denied"
