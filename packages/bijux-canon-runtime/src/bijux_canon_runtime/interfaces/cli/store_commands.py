# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Read-only storage commands for the runtime CLI."""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
from pathlib import Path
from typing import cast

from bijux_canon_runtime.observability.analysis.trace_diff import semantic_trace_diff
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
)
from bijux_canon_runtime.ontology.ids import RunID, TenantID


def normalize_for_json(value: object, *, normalize_timestamps: bool = False) -> object:
    """Normalize runtime values for deterministic CLI JSON output."""
    if isinstance(value, tuple):
        return [
            normalize_for_json(item, normalize_timestamps=normalize_timestamps)
            for item in value
        ]
    if isinstance(value, list):
        normalized = [
            normalize_for_json(item, normalize_timestamps=normalize_timestamps)
            for item in value
        ]
        if normalize_timestamps and all(isinstance(item, str) for item in normalized):
            return sorted(cast(list[str], normalized))
        return normalized
    if isinstance(value, dict):
        normalized_dict: dict[str, object] = {}
        for key, item in value.items():
            if normalize_timestamps and "timestamp" in key:
                normalized_dict[key] = "normalized"
            else:
                normalized_dict[key] = normalize_for_json(
                    item, normalize_timestamps=normalize_timestamps
                )
        return normalized_dict
    if hasattr(value, "value"):
        return value.value
    return value


def inspect_run(args: argparse.Namespace, *, json_output: bool) -> None:
    """Inspect a persisted runtime trace."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    trace = store.load_trace(RunID(args.run_id), tenant_id=TenantID(args.tenant_id))
    if json_output:
        payload = normalize_for_json(asdict(trace))
        print(json.dumps(payload, sort_keys=True))
        return
    print(
        f"Run {args.run_id}: events={len(trace.events)} "
        f"tool_invocations={len(trace.tool_invocations)} "
        f"entropy_entries={len(trace.entropy_usage)}"
    )


def diff_runs(args: argparse.Namespace, *, json_output: bool) -> None:
    """Compare two persisted runtime traces."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    tenant_id = TenantID(args.tenant_id)
    trace_a = store.load_trace(RunID(args.run_a), tenant_id=tenant_id)
    trace_b = store.load_trace(RunID(args.run_b), tenant_id=tenant_id)
    diff = semantic_trace_diff(
        trace_a, trace_b, acceptability=trace_a.replay_acceptability
    )
    if json_output:
        print(json.dumps(normalize_for_json(diff), sort_keys=True))
        return
    if diff:
        print(f"Diff detected: keys={', '.join(sorted(diff.keys()))}")
    else:
        print("Diff clean: no semantic differences")


def explain_failure(args: argparse.Namespace, *, json_output: bool) -> None:
    """Explain the last persisted failure for a runtime trace."""
    store = DuckDBExecutionReadStore(Path(args.db_path))
    trace = store.load_trace(RunID(args.run_id), tenant_id=TenantID(args.tenant_id))
    failure_events = [
        event
        for event in trace.events
        if event.event_type.value
        in {
            "STEP_FAILED",
            "RETRIEVAL_FAILED",
            "REASONING_FAILED",
            "VERIFICATION_FAIL",
            "TOOL_CALL_FAIL",
            "EXECUTION_INTERRUPTED",
        }
    ]
    payload = {
        "run_id": args.run_id,
        "failure": normalize_for_json(
            failure_events[-1].payload, normalize_timestamps=True
        )
        if failure_events
        else None,
        "event_type": failure_events[-1].event_type.value if failure_events else None,
    }
    if json_output:
        print(json.dumps(payload, sort_keys=True))
        return
    if failure_events:
        last = failure_events[-1]
        print(f"Failure {last.event_type.value}: {normalize_for_json(last.payload)}")
    else:
        print("No failure events recorded")


def validate_db(args: argparse.Namespace, *, json_output: bool) -> None:
    """Validate that a runtime execution store is readable."""
    DuckDBExecutionReadStore(Path(args.db_path))
    if json_output:
        print(json.dumps({"status": "ok"}, sort_keys=True))
        return
    print("DB validated: ok")


__all__ = [
    "diff_runs",
    "explain_failure",
    "inspect_run",
    "normalize_for_json",
    "validate_db",
]
