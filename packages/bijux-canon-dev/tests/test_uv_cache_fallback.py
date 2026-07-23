from __future__ import annotations

import os
from pathlib import Path
import subprocess

REPO_ROOT = Path(__file__).resolve().parents[3]
RESOLVER = REPO_ROOT / "makes" / "tooling" / "uv-cache-fallback.sh"


def _fake_uv(directory: Path) -> Path:
    executable = directory / "uv"
    executable.write_text(
        """#!/bin/sh
printf '%s\\n' "${UV_OFFLINE:-online}:$*" >> "$UV_INVOCATIONS"
if [ "${UV_OFFLINE:-}" = "1" ]; then
    exit 0
fi
exit 23
""",
        encoding="utf-8",
    )
    executable.chmod(0o755)
    return executable


def test_uv_install_retries_from_cache_after_online_failure(tmp_path: Path) -> None:
    _fake_uv(tmp_path)
    invocation_log = tmp_path / "uv-invocations.log"
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "UV_INVOCATIONS": str(invocation_log),
    }

    result = subprocess.run(
        [RESOLVER, "pip", "install", "--python", "/venv/bin/python", "demo"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 0
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "online:pip install --python /venv/bin/python demo",
        "1:pip install --python /venv/bin/python demo",
    ]
    assert "retrying from the local cache" in result.stderr


def test_uv_non_install_failure_preserves_online_status(tmp_path: Path) -> None:
    _fake_uv(tmp_path)
    invocation_log = tmp_path / "uv-invocations.log"
    environment = {
        **os.environ,
        "PATH": f"{tmp_path}{os.pathsep}{os.environ['PATH']}",
        "UV_INVOCATIONS": str(invocation_log),
    }

    result = subprocess.run(
        [RESOLVER, "venv", "--python", "python3.11", "/venv"],
        check=False,
        capture_output=True,
        env=environment,
        text=True,
    )

    assert result.returncode == 23
    assert invocation_log.read_text(encoding="utf-8").splitlines() == [
        "online:venv --python python3.11 /venv"
    ]
