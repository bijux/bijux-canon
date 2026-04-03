from __future__ import annotations

import os
import shutil
import subprocess
import sys


def _assert_help(command: list[str]) -> None:
    env = {
        "OPENAI_API_KEY": "test",
        "ANTHROPIC_API_KEY": "test",
        "HUGGINGFACE_API_KEY": "test",
        "DEEPSEEK_API_KEY": "test",
    }
    result = subprocess.run(
        command,
        check=False,
        capture_output=True,
        text=True,
        env={**os.environ, **env},
    )
    assert result.returncode == 0
    combined = (result.stdout or "") + (result.stderr or "")
    assert "Traceback" not in combined
    assert combined.strip()


def test_cli_help_commands() -> None:
    exe = shutil.which("bijux-agent")
    base_cmd = [sys.executable, "-m", "bijux_agent.main"] if exe is None else [exe]
    _assert_help([*base_cmd, "run", "--help"])
    _assert_help([*base_cmd, "replay", "--help"])
