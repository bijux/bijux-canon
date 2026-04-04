# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections import defaultdict, deque

from bijux_canon_reason.core.types import (
    Plan,
    Trace,
    TraceEventKind,
    VerificationReport,
)

SUPPORTED_TRACE_SCHEMA_VERSIONS = {1, 2}
SUPPORTED_RUNTIME_PROTOCOL_VERSIONS = {1}
SUPPORTED_CANONICALIZATION_VERSIONS = {1}
SUPPORTED_FINGERPRINT_ALGOS = {"sha256"}


def validate_plan(plan: Plan) -> list[str]:
    nodes_by_id = _plan_nodes_by_id(plan)
    return [
        *_duplicate_node_id_errors(plan),
        *_missing_dependency_errors(plan, nodes_by_id),
        *_cycle_errors(plan, nodes_by_id),
    ]


def validate_trace(trace: Trace, plan: Plan | None = None) -> list[str]:
    plan_nodes = set() if plan is None else {node.id for node in plan.nodes}
    state = _TraceValidationState(plan_nodes=plan_nodes)
    return [
        *_trace_header_errors(trace),
        *_trace_index_errors(trace),
        *_trace_linkage_errors(trace, state),
        *_trace_lifecycle_errors(trace, state),
    ]


def validate_verification_report(report: VerificationReport) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for check in report.checks:
        if check.name in seen:
            errors.append(f"Duplicate check name: {check.name}")
        seen.add(check.name)
    return errors


def _plan_nodes_by_id(plan: Plan) -> dict[str, object]:
    return {node.id: node for node in plan.nodes}


def _duplicate_node_id_errors(plan: Plan) -> list[str]:
    node_ids = [node.id for node in plan.nodes]
    if len(set(node_ids)) == len(node_ids):
        return []
    return ["Plan contains duplicate node ids."]


def _missing_dependency_errors(
    plan: Plan, nodes_by_id: dict[str, object]
) -> list[str]:
    return [
        f"PlanNode {node.id} depends on missing node id: {dependency}"
        for node in plan.nodes
        for dependency in node.dependencies
        if dependency not in nodes_by_id
    ]


def _cycle_errors(plan: Plan, nodes_by_id: dict[str, object]) -> list[str]:
    indegree = dict.fromkeys(nodes_by_id, 0)
    adjacency: dict[str, list[str]] = defaultdict(list)
    for node in plan.nodes:
        for dependency in node.dependencies:
            adjacency[dependency].append(node.id)
            indegree[node.id] += 1

    queue = deque([node_id for node_id, degree in indegree.items() if degree == 0])
    visited = 0
    while queue:
        source = queue.popleft()
        visited += 1
        for target in adjacency[source]:
            indegree[target] -= 1
            if indegree[target] == 0:
                queue.append(target)
    if visited == len(nodes_by_id):
        return []
    return ["Plan contains a cycle (DAG invariant violated)."]


class _TraceValidationState:
    def __init__(self, *, plan_nodes: set[str]) -> None:
        self.plan_nodes = plan_nodes
        self.tool_calls: set[str] = set()
        self.tool_results: set[str] = set()
        self.evidence_ids: set[str] = set()
        self.started_steps: set[str] = set()
        self.finished_steps: set[str] = set()


def _trace_header_errors(trace: Trace) -> list[str]:
    errors: list[str] = []
    if trace.schema_version not in SUPPORTED_TRACE_SCHEMA_VERSIONS:
        errors.append(
            f"Unsupported trace schema_version={trace.schema_version} "
            f"(supported: {sorted(SUPPORTED_TRACE_SCHEMA_VERSIONS)})"
        )
    if trace.runtime_protocol_version not in SUPPORTED_RUNTIME_PROTOCOL_VERSIONS:
        errors.append(
            "Unsupported trace runtime_protocol_version="
            f"{trace.runtime_protocol_version} "
            f"(supported: {sorted(SUPPORTED_RUNTIME_PROTOCOL_VERSIONS)})"
        )
    if trace.canonicalization_version not in SUPPORTED_CANONICALIZATION_VERSIONS:
        errors.append(
            "Unsupported trace canonicalization_version="
            f"{trace.canonicalization_version} "
            f"(supported: {sorted(SUPPORTED_CANONICALIZATION_VERSIONS)})"
        )
    if trace.fingerprint_algo not in SUPPORTED_FINGERPRINT_ALGOS:
        errors.append(
            f"Unsupported trace fingerprint_algo={trace.fingerprint_algo} "
            f"(supported: {sorted(SUPPORTED_FINGERPRINT_ALGOS)})"
        )
    return errors


def _trace_index_errors(trace: Trace) -> list[str]:
    errors: list[str] = []
    for idx, event in enumerate(trace.events):
        if event.idx is None:
            errors.append("Trace event missing idx field")
        elif event.idx != idx:
            errors.append("Trace idx must be monotonically increasing from 0")
    return errors


def _trace_linkage_errors(trace: Trace, state: _TraceValidationState) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        if event.kind == TraceEventKind.tool_called:
            if event.call.id in state.tool_calls:
                errors.append(f"Duplicate tool call id: {event.call.id}")
            state.tool_calls.add(event.call.id)
        elif event.kind == TraceEventKind.tool_returned:
            state.tool_results.add(event.result.call_id)
            if event.result.call_id not in state.tool_calls:
                errors.append(
                    f"ToolReturned references unknown call: {event.result.call_id}"
                )
        elif event.kind == TraceEventKind.evidence_registered:
            if not event.step_id:
                errors.append("Evidence event missing step_id")
            if event.evidence.id in state.evidence_ids:
                errors.append(f"Duplicate evidence id: {event.evidence.id}")
            state.evidence_ids.add(event.evidence.id)
    missing_results = state.tool_calls - state.tool_results
    if missing_results:
        errors.append(f"Missing tool results for call ids: {sorted(missing_results)}")
    return errors


def _trace_lifecycle_errors(trace: Trace, state: _TraceValidationState) -> list[str]:
    errors: list[str] = []
    for event in trace.events:
        if event.kind == TraceEventKind.step_started:
            state.started_steps.add(event.step_id)
            if state.plan_nodes and event.step_id not in state.plan_nodes:
                errors.append(f"step_started references unknown step {event.step_id}")
        elif event.kind == TraceEventKind.step_finished:
            state.finished_steps.add(event.step_id)
    unfinished_steps = state.started_steps - state.finished_steps
    if unfinished_steps:
        errors.append(f"Unfinished steps: {sorted(unfinished_steps)}")
    return errors
