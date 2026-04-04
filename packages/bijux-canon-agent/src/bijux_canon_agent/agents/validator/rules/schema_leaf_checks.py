"""Leaf and sequence validation helpers for recursive schema traversal."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from bijux_canon_agent.observability.logging import MetricType

RecursiveValidator = Callable[[Any, Any, Any, str], tuple[list[str], dict[str, Any]]]


def validate_list_branch(
    agent: Any,
    *,
    data: Any,
    schema: list[Any],
    path: str,
    tags: dict[str, str],
    validate_recursive: RecursiveValidator,
) -> tuple[list[str], dict[str, Any]]:
    """Validate a homogeneous list branch in the recursive schema walker."""
    errors: list[str] = []
    audit: dict[str, Any] = {}
    expected_type = schema[0]
    if not isinstance(data, list):
        error_msg = f"{path}: Expected list, got {type(data).__name__}"
        errors.append(error_msg)
        audit[path] = {
            "error": "type_mismatch",
            "expected": "list",
            "actual": type(data).__name__,
        }
        agent.logger.error(error_msg, extra={"context": tags})
        agent.logger_manager.log_metric(
            "type_mismatch_errors", 1, MetricType.COUNTER, tags=tags
        )
        return errors, audit
    for idx, item in enumerate(data):
        item_path = f"{path}[{idx}]"
        child_errors, child_audit = validate_recursive(
            agent, item, expected_type, item_path
        )
        errors.extend(child_errors)
        audit[item_path] = child_audit
    return errors, audit


def validate_terminal_branch(
    agent: Any,
    *,
    data: Any,
    schema: Any,
    path: str,
    tags: dict[str, str],
) -> tuple[list[str], dict[str, Any]]:
    """Validate a non-container schema branch."""
    errors: list[str] = []
    audit: dict[str, Any] = {}
    if not isinstance(data, schema):
        error_msg = f"{path}: Expected {schema.__name__}, got {type(data).__name__}"
        errors.append(error_msg)
        audit[path] = {
            "error": "type_mismatch",
            "expected": schema.__name__,
            "actual": type(data).__name__,
        }
        agent.logger.error(error_msg, extra={"context": tags})
        agent.logger_manager.log_metric(
            "type_mismatch_errors", 1, MetricType.COUNTER, tags=tags
        )
        return errors, audit
    audit[path] = {
        "value": data,
        "expected": schema.__name__,
        "type": type(data).__name__,
    }
    return errors, audit


__all__ = ["validate_list_branch", "validate_terminal_branch"]
