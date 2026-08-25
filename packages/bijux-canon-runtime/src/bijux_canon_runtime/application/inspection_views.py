# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded public views over complete authoritative Runtime inspection records."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import fields, is_dataclass
import hashlib

from bijux_canon_runtime.model.artifact import canonical_json_bytes

INLINE_INSPECTION_VALUE_BYTES = 512
MAX_INSPECTION_STRING_CHARACTERS = 512
MAX_INSPECTION_PAGE_SIZE = 100

_SEMANTIC_COLLECTIONS = {
    "budgets",
    "checks",
    "citations",
    "claims",
    "hits",
    "provider_calls",
    "queries",
    "tool_calls",
}


def bounded_inspection_record(record: Mapping[str, object]) -> dict[str, object]:
    """Replace arbitrary persisted values with integrity-bound bounded summaries."""
    counts = {
        key: len(value)
        for key, value in record.items()
        if isinstance(value, list | tuple)
    }
    bounded: dict[str, object] = {}
    for key, value in record.items():
        if not isinstance(value, list | tuple):
            bounded[key] = _bounded_structure(value)
            continue
        if key == "artifacts":
            bounded[key] = [_artifact_summary(item) for item in value]
        elif key in _SEMANTIC_COLLECTIONS:
            bounded[key] = [_semantic_summary(item) for item in value]
        elif key == "events":
            bounded[key] = [_event_summary(item) for item in value]
        else:
            bounded[key] = [_bounded_structure(item) for item in value]
    bounded["collection_counts"] = counts
    bounded["inspection_view"] = {
        "inline_value_max_bytes": INLINE_INSPECTION_VALUE_BYTES,
        "payload_access": "use the paginated artifact-payload operation",
        "schema_version": "bijux.runtime.inspection-view.v1",
        "value_mode": "bounded-summary",
    }
    return bounded


def _artifact_summary(value: object) -> object:
    """Expose artifact metadata while replacing its payload with a reference."""
    mapped = _mapping(value)
    if mapped is None:
        return _bounded_structure(value)
    summary = {str(key): item for key, item in mapped.items() if key != "json_value"}
    artifact_id = summary.get("artifact_id")
    json_value = mapped.get("json_value")
    summary["json_value"] = None if json_value is None else _value_reference(json_value)
    if isinstance(artifact_id, str):
        summary["payload_page_uri"] = f"/api/v2/artifacts/{artifact_id}/payload"
    return _bounded_structure(summary)


def _semantic_summary(value: object) -> object:
    """Retain semantic record structure without inlining an unbounded value."""
    mapped = _mapping(value)
    if mapped is None:
        return _bounded_structure(value)
    return {
        str(key): _value_reference(item) if key == "value" else _bounded_structure(item)
        for key, item in mapped.items()
    }


def _event_summary(value: object) -> object:
    """Retain event fields while integrity-binding an attached policy value."""
    mapped = _mapping(value)
    if mapped is None:
        return _bounded_structure(value)
    return {
        str(key): _value_reference(item)
        if key == "policy"
        else _bounded_structure(item)
        for key, item in mapped.items()
    }


def _value_reference(value: object) -> dict[str, object]:
    """Describe a canonical value and inline it only within the byte ceiling."""
    encoded = canonical_json_bytes(value)
    reference: dict[str, object] = {
        "byte_length": len(encoded),
        "sha256": hashlib.sha256(encoded).hexdigest(),
        "value_type": _value_type(value),
    }
    if len(encoded) <= INLINE_INSPECTION_VALUE_BYTES:
        reference["inline"] = _bounded_structure(value)
    return reference


def _bounded_structure(value: object) -> object:
    """Recursively bound strings while preserving container shape and identity."""
    if isinstance(value, str):
        if len(value) <= MAX_INSPECTION_STRING_CHARACTERS:
            return value
        return {
            "character_length": len(value),
            "prefix": value[:MAX_INSPECTION_STRING_CHARACTERS],
            "sha256": hashlib.sha256(value.encode("utf-8")).hexdigest(),
            "value_type": "string",
        }
    if isinstance(value, Mapping):
        return {str(key): _bounded_structure(item) for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {
            field.name: _bounded_structure(getattr(value, field.name))
            for field in fields(value)
        }
    if isinstance(value, list | tuple):
        return [_bounded_structure(item) for item in value]
    return value


def _mapping(value: object) -> Mapping[str, object] | None:
    """Project mappings and dataclass instances onto string-keyed records."""
    if isinstance(value, Mapping):
        return {str(key): item for key, item in value.items()}
    if is_dataclass(value) and not isinstance(value, type):
        return {field.name: getattr(value, field.name) for field in fields(value)}
    return None


def _value_type(value: object) -> str:
    """Return the stable JSON-oriented type name used in value references."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, str):
        return "string"
    if isinstance(value, int | float):
        return "number"
    if isinstance(value, Mapping):
        return "object"
    if isinstance(value, list | tuple):
        return "array"
    return type(value).__name__


__all__ = [
    "INLINE_INSPECTION_VALUE_BYTES",
    "MAX_INSPECTION_STRING_CHARACTERS",
    "MAX_INSPECTION_PAGE_SIZE",
    "bounded_inspection_record",
]
