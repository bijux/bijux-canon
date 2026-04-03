from __future__ import annotations

import sys
from types import SimpleNamespace

from bijux_agent.main import load_config, parse_args


def test_parse_args_run_command(monkeypatch) -> None:
    """parse_args() should parse the single run command with defaults."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["bijux-agent", "run", "dummy.txt", "--out", "results-dir"],
    )
    args = parse_args()
    assert args.command == "run"
    assert args.input_path == "dummy.txt"
    assert args.results_dir == "results-dir"
    assert args.config == "config/config.yml"
    assert args.dry_run is False
    assert args.replay is None


def test_parse_args_all_flags(monkeypatch) -> None:
    """parse_args() should respect the supported flags."""
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bijux-agent",
            "run",
            "another.txt",
            "--out",
            "out-dir",
            "--config",
            "custom.yml",
            "--dry-run",
            "--replay",
            "trace.json",
        ],
    )
    args = parse_args()
    assert args.command == "run"
    assert args.input_path == "another.txt"
    assert args.results_dir == "out-dir"
    assert args.config == "custom.yml"
    assert args.dry_run is True
    assert args.replay == "trace.json"


def test_parse_args_replay_command(monkeypatch) -> None:
    """parse_args() should accept the hidden replay helper."""
    monkeypatch.setattr(
        sys,
        "argv",
        ["bijux-agent", "replay", "trace.json"],
    )
    args = parse_args()
    assert args.command == "replay"
    assert args.trace_path == "trace.json"


def test_load_config_reads_yaml(tmp_path) -> None:
    """load_config() should parse YAML config files safely."""
    config_path = tmp_path / "test-config.yml"
    config_path.write_text("pipeline:\n  enabled: true\n")
    logger = SimpleNamespace(
        info=lambda *args, **kwargs: None,
        warning=lambda *args, **kwargs: None,
        error=lambda *args, **kwargs: None,
    )
    result = load_config(str(config_path), logger)
    assert result["pipeline"]["enabled"] is True
