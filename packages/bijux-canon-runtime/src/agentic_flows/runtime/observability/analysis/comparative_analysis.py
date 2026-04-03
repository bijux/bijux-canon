# ANALYSIS ONLY — NOT REQUIRED FOR EXECUTION OR REPLAY
# EXPERIMENTAL: API NOT STABLE
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/analysis/comparative_analysis.py."""

from __future__ import annotations

from collections.abc import Sequence
import logging

from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace

_LOGGER = logging.getLogger(__name__)


def compare_runs(traces: Sequence[ExecutionTrace]) -> dict[str, object]:
    """Compare runs; misuse hides divergence."""
    _LOGGER.warning(
        "experimental observability: comparative analysis output is not stable"
    )
    if not traces:
        return {"runs": 0}
    claim_sets = [set(trace.claim_ids) for trace in traces]
    if not claim_sets:
        claim_overlap = 1.0
    else:
        shared = set.intersection(*claim_sets) if claim_sets else set()
        union = set.union(*claim_sets) if claim_sets else set()
        claim_overlap = 1.0 if not union else len(shared) / len(union)
    contradiction_counts = [trace.contradiction_count for trace in traces]
    arbitration_decisions = [trace.arbitration_decision for trace in traces]
    return {
        "runs": len(traces),
        "claim_overlap": claim_overlap,
        "contradiction_min": min(contradiction_counts),
        "contradiction_max": max(contradiction_counts),
        "arbitration_decisions": sorted(set(arbitration_decisions)),
    }


__all__ = ["compare_runs"]
