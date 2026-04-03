# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


def test_plugin_contracts_report_json():
    repo_root = Path(__file__).resolve().parents[3]
    script = repo_root / "scripts" / "plugin_test_kit.py"
    result = subprocess.run(
        [sys.executable, str(script), "--format", "json"],
        check=True,
        capture_output=True,
        text=True,
    )
    payload = json.loads(result.stdout.strip())
    assert "summary" in payload
