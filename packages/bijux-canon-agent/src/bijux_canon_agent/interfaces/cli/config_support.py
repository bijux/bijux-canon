"""Configuration and directory helpers for the Bijux Agent CLI."""

from __future__ import annotations

from pathlib import Path
import sys
from typing import Any


def ensure_directory(path: str) -> None:
    """Ensure the directory exists, creating it if necessary."""
    if path:
        dir_path = Path(path).resolve()
        dir_path.mkdir(parents=True, exist_ok=True)


def load_config(config_path: str, logger: Any) -> dict[str, Any]:
    """Load configuration from a YAML file."""
    try:
        import yaml
    except ImportError:
        logger.error(
            "PyYAML required to load config file. Install with: pip install pyyaml"
        )
        sys.exit(1)

    path = Path(config_path)
    if not path.exists():
        logger.warning(f"Config file not found at {config_path}, using defaults")
        return {}

    try:
        with open(path, encoding="utf-8") as file:
            config = yaml.safe_load(file)
        if not isinstance(config, dict):
            logger.error(f"Config file must contain a dictionary, got {type(config)}")
            sys.exit(1)
        return config
    except Exception as exc:
        logger.error(f"Failed to load config file {config_path}: {exc}")
        sys.exit(1)


__all__ = ["ensure_directory", "load_config"]
