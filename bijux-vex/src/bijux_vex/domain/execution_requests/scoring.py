# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
import math

from bijux_vex.core.errors import ValidationError
from bijux_vex.core.types import Result


def _normalize_float(value: float) -> float:
    if not math.isfinite(value):
        raise ValidationError(message="Non-finite float detected in scoring")
    return float(value)


def l2_distance(query_vec: Iterable[float], target_vec: Iterable[float]) -> float:
    total = 0.0
    for q, t in zip(query_vec, target_vec, strict=True):
        diff = q - t
        total += diff * diff
    return _normalize_float(total)


def cosine_similarity(query_vec: Iterable[float], target_vec: Iterable[float]) -> float:
    num = 0.0
    q_norm = 0.0
    t_norm = 0.0
    for q, t in zip(query_vec, target_vec, strict=True):
        num += q * t
        q_norm += q * q
        t_norm += t * t
    denom = math.sqrt(q_norm) * math.sqrt(t_norm)
    if denom == 0:
        raise ValidationError(message="Zero-vector encountered in cosine scoring")
    return _normalize_float(num / denom)


def score(
    metric: str, query_vec: tuple[float, ...], target_vec: tuple[float, ...]
) -> float:
    if metric == "l2":
        return l2_distance(query_vec, target_vec)
    if metric == "cosine":
        # higher similarity -> use negative to keep lower-is-better ordering
        return -cosine_similarity(query_vec, target_vec)
    if metric == "dot":
        return _normalize_float(
            sum(q * t for q, t in zip(query_vec, target_vec, strict=True))
        )
    raise ValidationError(message=f"Unsupported metric: {metric}")


def tie_break_key(result: Result) -> tuple[float, str, str, str]:
    return (
        _normalize_float(result.score),
        result.vector_id,
        result.chunk_id,
        result.document_id,
    )
