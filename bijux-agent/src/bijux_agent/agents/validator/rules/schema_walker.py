"""Schema traversal helpers for ValidatorAgent."""

from __future__ import annotations

import re
from typing import Any

from bijux_agent.utilities.logger_manager import MetricType


def validate_recursive(
    agent: Any, data: Any, schema: Any, path: str
) -> tuple[list[str], dict[str, Any]]:
    """Recursively validate data against a schema."""
    from .schema_walker import validate_recursive  # For recursion

    errors: list[str] = []
    audit: dict[str, Any] = {}
    tags = {"stage": "validation", "path": path or "root"}

    if isinstance(schema, dict):
        if not isinstance(data, dict):
            error_msg = f"{path or 'root'}: Expected dict, got {type(data).__name__}"
            errors.append(error_msg)
            audit[path or "root"] = {
                "error": "type_mismatch",
                "expected": "dict",
                "actual": type(data).__name__,
            }
            agent.logger.error(error_msg, extra={"context": tags})
            agent.logger_manager.log_metric(
                "type_mismatch_errors", 1, MetricType.COUNTER, tags=tags
            )
            return errors, audit

        for key, rule in schema.items():
            val = data.get(key, None)
            key_path = f"{path}.{key}" if path else key
            key_tags = {"stage": "validation", "path": key_path}

            if isinstance(rule, dict):
                expected_type = rule.get("type")
                allowed = rule.get("allowed")
                required = rule.get("required", True)
                nested = rule.get("schema")
                default = rule.get("default")
                pattern = rule.get("pattern")
                condition = rule.get("condition")
                min_val = rule.get("min")
                max_val = rule.get("max")
                predicate = rule.get("predicate")
            else:
                expected_type = rule
                allowed = None
                required = True
                nested = None
                default = None
                pattern = None
                condition = None
                min_val = None
                max_val = None
                predicate = None

            if required and key not in data and default is not None:
                val = data[key] = default
                agent.logger.debug(
                    f"Applied default value for {key_path}",
                    extra={"context": key_tags},
                )
                agent.logger_manager.log_metric(
                    "default_values_applied", 1, MetricType.COUNTER, tags=key_tags
                )

            if required and key not in data:
                error_msg = f"{key_path}: Missing required key."
                errors.append(error_msg)
                audit[key_path] = {"error": "missing"}
                agent.logger.error(error_msg, extra={"context": key_tags})
                agent.logger_manager.log_metric(
                    "missing_key_errors", 1, MetricType.COUNTER, tags=key_tags
                )
                continue

            if key not in data:
                continue

            if condition and key in data:
                condition_key = condition.get("key")
                condition_type = condition.get("type")
                if condition_key in data and not isinstance(
                    data[condition_key], condition_type
                ):
                    error_msg = (
                        f"{key_path}: Condition failed - {condition_key} "
                        f"must be {condition_type.__name__}"
                    )
                    errors.append(error_msg)
                    audit[key_path] = {
                        "error": "condition_failed",
                        "condition": condition,
                    }
                    agent.logger.error(error_msg, extra={"context": key_tags})
                    agent.logger_manager.log_metric(
                        "condition_errors", 1, MetricType.COUNTER, tags=key_tags
                    )
                    continue

            if expected_type:
                val_checked = val
                try:
                    if agent.type_cast and not isinstance(val, expected_type):
                        if expected_type is int and isinstance(val, (str, float)):
                            val_checked = int(float(val))
                        elif expected_type is float and isinstance(val, str):
                            val_checked = float(val)
                        elif expected_type is str:
                            val_checked = str(val)
                        else:
                            raise ValueError(
                                f"Cannot cast {type(val).__name__} to "
                                f"{expected_type.__name__}"
                            )
                        data[key] = val_checked
                        agent.logger.debug(
                            f"Type cast successful for {key_path}",
                            extra={"context": key_tags},
                        )
                        agent.logger_manager.log_metric(
                            "type_cast_success",
                            1,
                            MetricType.COUNTER,
                            tags=key_tags,
                        )
                    elif not isinstance(val, expected_type):
                        error_msg = (
                            f"{key_path}: Expected {expected_type.__name__}, "
                            f"got {type(val).__name__}"
                        )
                        errors.append(error_msg)
                        audit[key_path] = {
                            "error": "type_mismatch",
                            "expected": expected_type.__name__,
                            "actual": type(val).__name__,
                        }
                        agent.logger.error(error_msg, extra={"context": key_tags})
                        agent.logger_manager.log_metric(
                            "type_mismatch_errors",
                            1,
                            MetricType.COUNTER,
                            tags=key_tags,
                        )
                        continue

                    if (
                        pattern
                        and isinstance(expected_type, type)
                        and expected_type is str
                        and not re.match(pattern, val_checked)
                    ):
                        error_msg = (
                            f"{key_path}: Value '{val_checked}' does not match "
                            f"pattern {pattern}"
                        )
                        errors.append(error_msg)
                        audit[key_path] = {
                            "error": "pattern_mismatch",
                            "pattern": str(pattern),
                            "value": val_checked,
                        }
                        agent.logger.error(error_msg, extra={"context": key_tags})
                        agent.logger_manager.log_metric(
                            "pattern_mismatch_errors",
                            1,
                            MetricType.COUNTER,
                            tags=key_tags,
                        )
                        continue

                    if (
                        (min_val is not None or max_val is not None)
                        and isinstance(expected_type, type)
                        and expected_type in (int, float)
                    ):
                        if min_val is not None and val_checked < min_val:
                            error_msg = (
                                f"{key_path}: Value {val_checked} is below "
                                f"minimum {min_val}"
                            )
                            errors.append(error_msg)
                            audit[key_path] = {
                                "error": "range_violation",
                                "min": min_val,
                                "value": val_checked,
                            }
                            agent.logger.error(error_msg, extra={"context": key_tags})
                            agent.logger_manager.log_metric(
                                "range_violation_errors",
                                1,
                                MetricType.COUNTER,
                                tags=key_tags,
                            )
                            continue
                        if max_val is not None and val_checked > max_val:
                            error_msg = (
                                f"{key_path}: Value {val_checked} exceeds "
                                f"maximum {max_val}"
                            )
                            errors.append(error_msg)
                            audit[key_path] = {
                                "error": "range_violation",
                                "max": max_val,
                                "value": val_checked,
                            }
                            agent.logger.error(error_msg, extra={"context": key_tags})
                            agent.logger_manager.log_metric(
                                "range_violation_errors",
                                1,
                                MetricType.COUNTER,
                                tags=key_tags,
                            )
                            continue

                    if predicate and not predicate(val_checked):
                        error_msg = (
                            f"{key_path}: Value {val_checked} failed custom "
                            f"predicate check"
                        )
                        errors.append(error_msg)
                        audit[key_path] = {
                            "error": "predicate_failed",
                            "value": val_checked,
                        }
                        agent.logger.error(error_msg, extra={"context": key_tags})
                        agent.logger_manager.log_metric(
                            "predicate_errors",
                            1,
                            MetricType.COUNTER,
                            tags=key_tags,
                        )
                        continue

                    if nested:
                        child_errors, child_audit = validate_recursive(
                            agent, val_checked, nested, key_path
                        )
                        errors.extend(child_errors)
                        audit[key_path] = child_audit
                    else:
                        audit[key_path] = {
                            "value": val_checked,
                            "type": type(val_checked).__name__,
                            "expected": expected_type.__name__,
                            "allowed": allowed,
                            "required": required,
                        }
                except Exception as e:
                    error_msg = f"{key_path}: Type cast failed ({e!s})"
                    errors.append(error_msg)
                    audit[key_path] = {
                        "error": "type_cast_failed",
                        "exception": str(e),
                    }
                    agent.logger.error(error_msg, extra={"context": key_tags})
                    agent.logger_manager.log_metric(
                        "type_cast_errors", 1, MetricType.COUNTER, tags=key_tags
                    )
                    continue

                if allowed and val not in allowed:
                    error_msg = (
                        f"{key_path}: Value '{val}' not in allowed set {allowed}"
                    )
                    errors.append(error_msg)
                    audit[key_path] = {
                        "error": "invalid_value",
                        "allowed": allowed,
                        "value": val,
                    }
                    agent.logger.error(error_msg, extra={"context": key_tags})
                    agent.logger_manager.log_metric(
                        "invalid_value_errors",
                        1,
                        MetricType.COUNTER,
                        tags=key_tags,
                    )

    elif isinstance(schema, list) and len(schema) == 1:
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
    else:
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
        else:
            audit[path] = {
                "value": data,
                "expected": schema.__name__,
                "type": type(data).__name__,
            }

    return errors, audit


def get_all_schema_keys(schema: dict[str, Any], path: str = "") -> set[str]:
    keys = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            full_key = f"{path}.{key}" if path else key
            keys.add(full_key)
            if isinstance(value, dict) and "schema" in value:
                keys.update(get_all_schema_keys(value["schema"], full_key))
    return keys


def get_all_data_keys(data: dict[str, Any], path: str = "") -> set[str]:
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{path}.{key}" if path else key
            keys.add(full_key)
            if isinstance(value, dict):
                keys.update(get_all_data_keys(value, full_key))
    return keys
