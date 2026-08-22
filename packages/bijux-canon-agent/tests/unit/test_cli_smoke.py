from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys

API_KEY_VARIABLES = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
    "HUGGINGFACE_API_KEY",
    "DEEPSEEK_API_KEY",
}


def _base_command() -> list[str]:
    exe = shutil.which("bijux-canon-agent")
    return [sys.executable, "-m", "bijux_canon_agent"] if exe is None else [exe]


def _credential_free_environment() -> dict[str, str]:
    return {
        key: value for key, value in os.environ.items() if key not in API_KEY_VARIABLES
    }


def _assert_help(command: list[str]) -> None:
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env=_credential_free_environment(),
    )
    assert result.returncode == 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Traceback" not in combined
    assert combined.strip()


def test_cli_help_commands() -> None:
    base_cmd = _base_command()
    _assert_help([*base_cmd, "--help"])
    _assert_help([*base_cmd, "--version"])
    _assert_help([*base_cmd, "run", "--help"])
    _assert_help([*base_cmd, "replay", "--help"])


def test_cli_run_requires_provider_credentials(tmp_path: Path) -> None:
    result = subprocess.run(
        [
            *_base_command(),
            "run",
            str(tmp_path / "missing-input"),
            "--out",
            str(tmp_path / "results"),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_credential_free_environment(),
    )

    assert result.returncode == 1
    assert "API key validation failed: Missing API keys" in result.stderr
