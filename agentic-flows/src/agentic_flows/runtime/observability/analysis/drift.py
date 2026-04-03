# ANALYSIS ONLY — NOT REQUIRED FOR EXECUTION OR REPLAY
# EXPERIMENTAL: API NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/analysis/drift.py."""

from __future__ import annotations


def entropy_drift(
    previous: dict[str, object],
    current: dict[str, object],
    *,
    max_count_delta: int,
    allow_new_sources: bool,
) -> dict[str, object]:
    """Compute entropy drift; misuse hides nondeterminism."""
    diffs: dict[str, object] = {}
    prev_sources = set(previous.get("sources", []))
    curr_sources = set(current.get("sources", []))
    if not allow_new_sources and curr_sources != prev_sources:
        diffs["sources"] = {
            "expected": sorted(prev_sources),
            "observed": sorted(curr_sources),
        }
    prev_count = int(previous.get("count", 0))
    curr_count = int(current.get("count", 0))
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
