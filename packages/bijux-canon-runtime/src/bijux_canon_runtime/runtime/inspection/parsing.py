# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Strict JSON parsing helpers for persisted Runtime metadata."""

from __future__ import annotations

import json

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.runtime.inspection.models import RuntimeInspectionError


def json_object(artifact: AddressedArtifact) -> dict[str, object]:
    """Decode a required JSON object from a metadata artifact."""
    if artifact.descriptor.media_type != "application/json":
        raise RuntimeInspectionError("Runtime metadata artifact is not JSON")
    try:
        return required_dict(json.loads(artifact.canonical_bytes), "artifact payload")
    except json.JSONDecodeError as exc:
        raise RuntimeInspectionError(
            "Runtime metadata artifact is invalid JSON"
        ) from exc


def required_dict(value: object, description: str) -> dict[str, object]:
    """Require an object with string keys."""
    if not isinstance(value, dict) or any(not isinstance(key, str) for key in value):
        raise RuntimeInspectionError(f"{description} must be a JSON object")
    return value


def required_object(record: dict[str, object], key: str) -> dict[str, object]:
    """Require one nested object field."""
    return required_dict(record.get(key), key)


def required_list(record: dict[str, object], key: str) -> list[object]:
    """Require one array field."""
    value = record.get(key)
    if not isinstance(value, list):
        raise RuntimeInspectionError(f"{key} must be a JSON array")
    return value


def required_string(
    record: dict[str, object],
    key: str,
    *,
    permit_empty: bool = False,
) -> str:
    """Require one string field."""
    value = record.get(key)
    if not isinstance(value, str) or (not permit_empty and not value.strip()):
        raise RuntimeInspectionError(f"{key} must be a nonempty string")
    return value


def optional_string(record: dict[str, object], key: str) -> str | None:
    """Require one nullable string field."""
    value = record.get(key)
    if value is None:
        return None
    if not isinstance(value, str) or not value.strip():
        raise RuntimeInspectionError(f"{key} must be null or a nonempty string")
    return value


def required_integer(record: dict[str, object], key: str) -> int:
    """Require one nonnegative integer field."""
    value = record.get(key)
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise RuntimeInspectionError(f"{key} must be a nonnegative integer")
    return value


def required_string_list(value: object, description: str) -> list[str]:
    """Require an array containing only strings."""
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise RuntimeInspectionError(f"{description} must contain strings")
    return value


def required_strings(record: dict[str, object], key: str) -> tuple[str, ...]:
    """Require one array field and return its strings as a tuple."""
    return tuple(required_string_list(record.get(key), key))


__all__ = [
    "json_object",
    "optional_string",
    "required_dict",
    "required_integer",
    "required_list",
    "required_object",
    "required_string",
    "required_string_list",
    "required_strings",
]
