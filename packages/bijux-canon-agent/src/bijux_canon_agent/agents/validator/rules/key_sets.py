"""Recursive key-set helpers for validator schemas and payloads."""

from __future__ import annotations

from typing import Any


def get_all_schema_keys(schema: dict[str, Any], path: str = "") -> set[str]:
    """Return the recursive key set defined by a validation schema."""
    keys = set()
    if isinstance(schema, dict):
        for key, value in schema.items():
            full_key = f"{path}.{key}" if path else key
            keys.add(full_key)
            if isinstance(value, dict) and "schema" in value:
                keys.update(get_all_schema_keys(value["schema"], full_key))
    return keys


def get_all_data_keys(data: dict[str, Any], path: str = "") -> set[str]:
    """Return the recursive key set present in a data payload."""
    keys = set()
    if isinstance(data, dict):
        for key, value in data.items():
            full_key = f"{path}.{key}" if path else key
            keys.add(full_key)
            if isinstance(value, dict):
                keys.update(get_all_data_keys(value, full_key))
    return keys
