# ANALYSIS ONLY — NOT REQUIRED FOR EXECUTION OR REPLAY
# EXPERIMENTAL: API NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for observability/analysis/drift.py."""

from __future__ import annotations

from collections.abc import Iterable


def entropy_drift(
    previous: dict[str, object],
    current: dict[str, object],
    *,
    max_count_delta: int,
    allow_new_sources: bool,
) -> dict[str, object]:
    """Compute entropy drift; misuse hides nondeterminism."""
    diffs: dict[str, object] = {}
    prev_sources = _source_set(previous.get("sources"))
    curr_sources = _source_set(current.get("sources"))
    if not allow_new_sources and curr_sources != prev_sources:
        diffs["sources"] = {
            "expected": sorted(prev_sources),
            "observed": sorted(curr_sources),
        }
    prev_count = _coerce_count(previous.get("count"))
    curr_count = _coerce_count(current.get("count"))
    if abs(curr_count - prev_count) > max_count_delta:
        diffs["count"] = {"expected": prev_count, "observed": curr_count}
    if previous.get("max_magnitude") != current.get("max_magnitude"):
        diffs["max_magnitude"] = {
            "expected": previous.get("max_magnitude"),
            "observed": current.get("max_magnitude"),
        }
    return diffs


def outcome_drift(
    previous: dict[str, object],
    current: dict[str, object],
) -> dict[str, object]:
    """Compute outcome drift; misuse hides artifact divergence."""
    diffs: dict[str, object] = {}
    for key in ("claim_count", "contradiction_count", "arbitration_decision"):
        if previous.get(key) != current.get(key):
            diffs[key] = {"expected": previous.get(key), "observed": current.get(key)}
    return diffs


__all__ = ["entropy_drift", "outcome_drift"]


def _source_set(value: object) -> set[str]:
    """Normalize a serialized source collection into a stable set."""
    if not isinstance(value, Iterable) or isinstance(value, str | bytes):
        return set()
    return {str(item) for item in value}


def _coerce_count(value: object) -> int:
    """Normalize count payloads without raising on malformed values."""
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        try:
            return int(value)
        except ValueError:
            return 0
    return 0
