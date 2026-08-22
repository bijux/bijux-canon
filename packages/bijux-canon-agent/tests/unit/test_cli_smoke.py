from __future__ import annotations

import json
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


def test_cli_replay_needs_no_provider_credentials(tmp_path: Path) -> None:
    trace = Path(__file__).parents[2] / "examples" / "golden" / "trace" / "run_trace.json"
    result = subprocess.run(
        [*_base_command(), "replay", str(trace)],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_credential_free_environment(),
    )

    assert result.returncode == 0, result.stderr
    assert "Reconstructed pipeline verdict" in result.stdout
    assert "API key validation failed" not in result.stderr


def test_cli_run_validates_input_without_provider_credentials(tmp_path: Path) -> None:
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

    assert result.returncode == 2
    combined = result.stdout + result.stderr
    assert "Input path does not exist" in combined
    assert "API key validation failed" not in combined


def test_cli_dry_run_needs_no_provider_credentials(tmp_path: Path) -> None:
    source = tmp_path / "research-note.txt"
    source.write_text("Observed evidence from a local research document.")
    results_dir = tmp_path / "results"

    result = subprocess.run(
        [
            *_base_command(),
            "run",
            str(source),
            "--out",
            str(results_dir),
            "--dry-run",
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_credential_free_environment(),
    )

    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "API key validation failed" not in combined
    assert (results_dir / "result" / "final_result.json").is_file()


def test_cli_local_profile_needs_no_provider_credentials(tmp_path: Path) -> None:
    source = tmp_path / "research-note.txt"
    source.write_text(
        "The observed samples share a dated genetic lineage. "
        "Independent measurements support the reported chronology. "
        "The limited sample size constrains broader interpretation."
    )
    config = tmp_path / "local.yml"
    config.write_text(
        "backend: simple\n"
        "strategy: extractive\n"
        "model_metadata:\n"
        "  provider: local\n"
        "  model_name: extractive-simple\n"
        "  temperature: 0.0\n"
        "  max_tokens: 512\n"
    )
    results_dir = tmp_path / "results"

    result = subprocess.run(
        [
            *_base_command(),
            "run",
            str(source),
            "--config",
            str(config),
            "--out",
            str(results_dir),
        ],
        check=False,
        capture_output=True,
        text=True,
        cwd=tmp_path,
        env=_credential_free_environment(),
    )

    assert result.returncode == 0, result.stderr
    combined = result.stdout + result.stderr
    assert "API key validation failed" not in combined
    final_result = json.loads(
        (results_dir / "result" / "final_result.json").read_text()
    )
    assert final_result["runtime_version"]
    assert final_result["model_metadata"]["provider"] == "local"
