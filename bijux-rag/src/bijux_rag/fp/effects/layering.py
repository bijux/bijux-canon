# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Bijux RAG: Container layering helpers (effects; no monad transformers)."""

from __future__ import annotations

from typing import TypeVar

from bijux_rag.result.types import Err, NoneVal, Ok, Option, Result, Some

T = TypeVar("T")
E = TypeVar("E")


def transpose_result_option(ro: Result[Option[T], E]) -> Option[Result[T, E]]:
    """Swap layers: Result[Option[T]] → Option[Result[T, E]].

    Error dominates absence: Err(e) becomes Some(Err(e)).
    """

    if isinstance(ro, Err):
        return Some(Err(ro.error))
    if isinstance(ro.value, Some):
        return Some(Ok(ro.value.value))
    return NoneVal()


def transpose_option_result(or_: Option[Result[T, E]]) -> Result[Option[T], E]:
    """Swap layers: Option[Result[T, E]] → Result[Option[T], E].

    Error dominates absence: Some(Err(e)) becomes Err(e).
    """

    if isinstance(or_, NoneVal):
        return Ok(NoneVal())

    inner = or_.value
    if isinstance(inner, Err):
        return Err(inner.error)
    return Ok(Some(inner.value))


__all__ = ["transpose_result_option", "transpose_option_result"]
