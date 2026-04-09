# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
"""Params helpers."""

from __future__ import annotations


def resolve_space(metric: str, override: str | None) -> str:
    """Resolve space."""
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
    """Coerce to int."""
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
