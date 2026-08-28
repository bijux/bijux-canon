# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Shared result accessors for ingest end-to-end tests."""

from __future__ import annotations

from dataclasses import is_dataclass
from typing import Any

import pytest

from bijux_canon_ingest.result import Err, Ok


def get_value(obj: Any, key: str, default: Any = None) -> Any:
    if isinstance(obj, dict):
        return obj.get(key, default)
    if is_dataclass(obj):
        return getattr(obj, key, default)
    return getattr(obj, key, default)


def unwrap_ok(maybe_result: Any, *, what: str) -> Any:
    """Return a successful result payload or fail with its typed error."""

    if isinstance(maybe_result, Ok):
        return maybe_result.value
    if isinstance(maybe_result, Err):
        pytest.fail(f"{what} returned Err: {maybe_result.error}")
    return maybe_result


__all__ = ["get_value", "unwrap_ok"]
