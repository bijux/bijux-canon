# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG Core 2: optional `returns` interop (end-of-Bijux RAG).

Policy:
- `returns` is boundary-only. Convert immediately into our `Result` / `Option`.
- This module is safe to import without `returns` installed.
"""

from __future__ import annotations

import importlib
from typing import Any, TypeVar

from bijux_rag.result.types import NONE, Err, ErrInfo, Ok, Option, Result, Some

T = TypeVar("T")


def _returns() -> Any | None:
    try:
        return importlib.import_module("returns")
    except Exception:
        return None


RETURNS_AVAILABLE: bool = _returns() is not None


def to_result(obj: Any, *, map_exc: Any | None = None) -> Result[Any, ErrInfo]:
    """Convert a `returns.result.Result` into `bijux_rag.result.types.Result`.

    If `returns` is not installed, raises ImportError.
    """

    if not RETURNS_AVAILABLE:
        raise ImportError("returns is not available")

    try:
        # `returns.result.Success` / `returns.result.Failure`
        if obj.__class__.__name__ == "Success":
            return Ok(obj._inner_value)
        if obj.__class__.__name__ == "Failure":
            inner = obj._inner_value
            if isinstance(inner, BaseException):
                return Err(ErrInfo.from_exception(inner))
            if map_exc is not None:
                return Err(map_exc(inner))
            return Err(ErrInfo(code="FAILURE", msg=str(inner)))
    except Exception as exc:  # pragma: no cover - defensive
        return Err(ErrInfo.from_exception(exc))

    return Err(ErrInfo(code="UNSUPPORTED", msg=f"unsupported returns object: {type(obj).__name__}"))


def to_option(obj: Any) -> Option[Any]:
    """Convert a `returns.maybe.Maybe` into `bijux_rag.result.types.Option`."""

    if not RETURNS_AVAILABLE:
        raise ImportError("returns is not available")

    try:
        if obj.__class__.__name__ == "Some":
            return Some(obj._inner_value)
        if obj.__class__.__name__ == "Nothing":
            return NONE
    except Exception as exc:  # pragma: no cover - defensive
        raise RuntimeError("invalid returns object") from exc

    raise ValueError(f"unsupported returns object: {type(obj).__name__}")


__all__ = ["RETURNS_AVAILABLE", "to_result", "to_option"]
