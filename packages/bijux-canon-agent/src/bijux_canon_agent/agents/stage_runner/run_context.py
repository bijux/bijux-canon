"""Run-context helpers for stage runner execution."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


def validate_stage_runner_context(context: Mapping[str, Any]) -> str | None:
    """Validate the minimum inputs required to execute a stage sequence."""
    if "file_path" in context:
        return None
    return "Input context must provide 'file_path' for stage execution"


def stage_skip_warning(
    stage: Mapping[str, Any],
    current_context: Mapping[str, Any],
) -> str | None:
    """Return the standardized warning when a stage condition is not met."""
    condition = stage.get("condition", lambda _: True)
    if condition(current_context):
        return None
    return f"Stage '{stage['name']}' skipped due to unmet condition"


def apply_stage_output_to_context(
    current_context: dict[str, Any],
    *,
    stage: Mapping[str, Any],
    stage_output: dict[str, Any],
) -> None:
    """Project a stage output back into the current workflow context."""
    output_key = stage.get("output_key", stage["name"])
    current_context[str(output_key)] = stage_output


__all__ = [
    "apply_stage_output_to_context",
    "stage_skip_warning",
    "validate_stage_runner_context",
]
