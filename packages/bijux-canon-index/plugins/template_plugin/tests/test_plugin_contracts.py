# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_plugin_contracts_report_json():
    package_root = Path(__file__).resolve().parents[3]
    repo_root = package_root.parents[1]
    script = repo_root / "scripts" / "bijux-canon-index" / "plugin_test_kit.py"
    result = subprocess.run(
        [sys.executable, str(script), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
        cwd=package_root,
    )
    payload = json.loads(result.stdout.strip())
    assert "summary" in payload
