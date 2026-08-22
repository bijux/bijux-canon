"""Compatibility helpers for the Bijux Agent CLI."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any
import uuid

from bijux_canon_agent.application.execution_service import process_input_files
from bijux_canon_agent.interfaces.cli import config_support as _config_support_module
from bijux_canon_agent.interfaces.cli import replay_support as _replay_support_module
from bijux_canon_agent.interfaces.cli import (
    result_artifacts as _result_artifacts_module,
)
from bijux_canon_agent.pipeline.canonical import AuditableDocPipeline
from bijux_canon_agent.traces import RunTrace


async def process_files(
    pipeline: AuditableDocPipeline,
    files: list[Path],
    task_goal: str,
    logger: Any,
    dry_run: bool = False,
) -> dict[str, Any]:
    """Process a list of files using the pipeline."""
    return await process_input_files(
        pipeline=pipeline,
        files=files,
        task_goal=task_goal,
        logger=logger,
        dry_run=dry_run,
    )


def build_trace_from_result(*args: Any, **kwargs: Any) -> tuple[Path, RunTrace]:
    """Build a run trace while preserving helper-level monkeypatch compatibility."""
    _result_artifacts_module.datetime = datetime
    _result_artifacts_module.uuid = uuid
    return _result_artifacts_module.build_trace_from_result(*args, **kwargs)


def write_final_artifacts(*args: Any, **kwargs: Any) -> Path:
    """Write final artifacts through the compatibility helper facade."""
    return _result_artifacts_module.write_final_artifacts(*args, **kwargs)


def load_config(*args: Any, **kwargs: Any) -> dict[str, Any]:
    """Load CLI configuration through the compatibility helper facade."""
    return _config_support_module.load_config(*args, **kwargs)


def handle_replay(trace_path: Path) -> None:
    """Replay a stored trace through the compatibility helper facade."""
    _replay_support_module.handle_replay(trace_path)


def load_trace(trace_path: Path) -> RunTrace:
    """Load a stored trace through the compatibility helper facade."""
    return _replay_support_module.load_trace(trace_path)


__all__ = [
    "build_trace_from_result",
    "handle_replay",
    "load_config",
    "load_trace",
    "process_files",
    "write_final_artifacts",
]
