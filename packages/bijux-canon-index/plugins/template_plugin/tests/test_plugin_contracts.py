# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys


def test_plugin_contracts_report_json():
    package_root = Path(__file__).resolve().parents[3]
    repo_root = package_root.parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = os.pathsep.join(
        [
            str(repo_root / "packages" / "bijux-canon-dev" / "src"),
            str(package_root / "src"),
        ]
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "bijux_canon_dev.packages.index.plugin_contract_report",
            "--format",
            "json",
        ],
        check=True,
        capture_output=True,
        text=True,
        cwd=package_root,
        env=env,
    )
    payload = json.loads(result.stdout.strip())
    assert "summary" in payload
