"""Runtime setup helpers for the Bijux Canon Agent CLI."""

from __future__ import annotations

import logging
from pathlib import Path
import sys
from typing import Any

from bijux_canon_agent.interfaces.cli.config_support import ensure_directory
from bijux_canon_agent.observability.logging import LoggerConfig, LoggerManager


def create_bootstrap_logger() -> logging.Logger:
    """Create the bootstrap logger used before full config is loaded."""
    bootstrap_logger = logging.getLogger("bijux_canon_agent.bootstrap")
    bootstrap_logger.setLevel(logging.INFO)
    if not bootstrap_logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(logging.Formatter("%(levelname)s: %(message)s"))
        bootstrap_logger.addHandler(handler)
    return bootstrap_logger


def create_logger_manager(config: dict[str, Any]) -> LoggerManager:
    """Create the runtime logger manager from CLI configuration."""
    logging_config = config.get("logging", {})
    log_dir = logging_config.get("log_dir", "artifacts/bijux-canon-agent/test/logs")
    log_level = logging_config.get("log_level", "INFO")
    log_file_name = logging_config.get("log_file_name", "application.log")
    structured_logging = logging_config.get("structured_logging", True)
    async_logging = logging_config.get("async_logging", True)
    telemetry_enabled = logging_config.get("telemetry_enabled", True)

    ensure_directory(log_dir)
    logger_config = LoggerConfig(
        log_dir=log_dir,
        log_level=log_level,
        log_file_name=log_file_name,
        structured_logging=structured_logging,
        async_logging=async_logging,
        telemetry_enabled=telemetry_enabled,
    )
    return LoggerManager(name="Bijux Agent", config=logger_config)


def resolve_input_files(input_path: Path) -> list[Path]:
    """Resolve a CLI input path to the list of files to process."""
    if not input_path.exists():
        raise FileNotFoundError(str(input_path))
    if input_path.is_file():
        return [input_path]
    if input_path.is_dir():
        files = [file for file in input_path.iterdir() if file.is_file()]
        if not files:
            raise RuntimeError(
                "Input directory is empty; add documents (e.g. .txt, .md) and retry."
            )
        return files
    raise ValueError(
        f"Invalid input path: {input_path} (neither a file nor a directory)"
    )


__all__ = ["create_bootstrap_logger", "create_logger_manager", "resolve_input_files"]
