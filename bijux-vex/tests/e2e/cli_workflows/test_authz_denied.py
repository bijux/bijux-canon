# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest


def test_cli_denies_mutations_when_authz_disabled(tmp_path: Path, monkeypatch):
    env = os.environ.copy()
    env["BIJUX_VEX_STATE_PATH"] = str(tmp_path / "authz.sqlite")
    env["BIJUX_VEX_AUTHZ_MODE"] = "deny"
    monkeypatch.chdir(tmp_path)
    cmd = [
        sys.executable,
        "-m",
        "bijux_vex.boundaries.cli.app",
        "ingest",
        "--doc",
        "hi",
        "--vector",
        json.dumps([0.0, 0.0]),
        "--vector-store",
        "memory",
    ]
    with pytest.raises(subprocess.CalledProcessError) as err:
        subprocess.check_output(cmd, text=True, env=env)
    assert err.value.returncode == 6
