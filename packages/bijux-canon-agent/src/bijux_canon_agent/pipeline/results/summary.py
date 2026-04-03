"""Summary merging helpers for pipeline results."""

from __future__ import annotations

from collections.abc import Sequence
import time
from typing import Any


def merge_summary_outputs(step_outputs: Sequence[dict[str, Any]]) -> dict[str, Any]:
    """Construct the merged summary output from multiple shards."""

    executive_summaries = []
    key_points: list[Any] = []
    actionable_insights = []
    critical_risks = []
    missing_info = []
    for output in step_outputs:
        summary = output.get("summary", {})
        executive_summaries.append(summary.get("executive_summary", ""))
        key_points.extend(summary.get("key_points", []))
        actionable_insights.append(summary.get("actionable_insights", ""))
        critical_risks.append(summary.get("critical_risks", ""))
        missing_info.append(summary.get("missing_info", ""))

    return {
        "summary": {
            "executive_summary": " ".join(s for s in executive_summaries if s),
            "key_points": list(dict.fromkeys(key_points)),
            "actionable_insights": (
                " ".join(s for s in actionable_insights if s)
                or "No actionable insights available"
            ),
            "critical_risks": (
                " ".join(s for s in critical_risks if s)
                or "No critical risks identified"
            ),
            "missing_info": (
                " ".join(s for s in missing_info if s) or "No missing information noted"
            ),
        },
        "method": step_outputs[0].get("method", "unknown")
        if step_outputs
        else "unknown",
        "input_length": sum(output.get("input_length", 0) for output in step_outputs),
        "backend": step_outputs[0].get("backend", "unknown")
        if step_outputs
        else "unknown",
        "strategy": step_outputs[0].get("strategy", "unknown")
        if step_outputs
        else "unknown",
        "audit": {
            "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "shards_merged": len(step_outputs),
        },
    }
