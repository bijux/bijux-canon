# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations


def resolve_space(metric: str, override: str | None) -> str:
    if override:
        return override
    if metric == "dot":
        return "ip"
    if metric == "cosine":
        return "cosine"
    if metric == "ip":
        return "ip"
    return "l2"


def as_int(value: object, default: int) -> int:
    if isinstance(value, bool):
        return default
    if isinstance(value, (int, float)):
        return int(value)
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return default
    return default
