# ANALYSIS ONLY — NOT REQUIRED FOR EXECUTION OR REPLAY
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/analysis/flow_correlation.py."""

from __future__ import annotations

from collections.abc import Iterable

from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace


def validate_flow_correlation(
    trace: ExecutionTrace, related_traces: Iterable[ExecutionTrace]
) -> None:
    """Validate flow correlation; misuse breaks cross-flow integrity."""
    related_ids = {item.flow_id for item in related_traces}
    if trace.parent_flow_id is not None and trace.parent_flow_id not in related_ids:
        raise ValueError("parent_flow_id missing from related traces")
    missing_children = set(trace.child_flow_ids).difference(related_ids)
    if missing_children:
        raise ValueError("child_flow_ids missing from related traces")


__all__ = ["validate_flow_correlation"]
