# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections import defaultdict, deque

from bijux_rar.core.rar_types import Plan, Trace, TraceEventKind, VerificationReport

SUPPORTED_TRACE_SCHEMA_VERSIONS = {1, 2}
SUPPORTED_RUNTIME_PROTOCOL_VERSIONS = {1}
SUPPORTED_CANONICALIZATION_VERSIONS = {1}
SUPPORTED_FINGERPRINT_ALGOS = {"sha256"}


def validate_plan(plan: Plan) -> list[str]:
    errors: list[str] = []
    node_ids = [n.id for n in plan.nodes]
    if len(set(node_ids)) != len(node_ids):
        errors.append("Plan contains duplicate node ids.")

    nodes_by_id = {n.id: n for n in plan.nodes}
    errors.extend(
        f"PlanNode {n.id} depends on missing node id: {dep}"
        for n in plan.nodes
        for dep in n.dependencies
        if dep not in nodes_by_id
    )

    indeg = dict.fromkeys(nodes_by_id, 0)
    adj: dict[str, list[str]] = defaultdict(list)
    for n in plan.nodes:
        for dep in n.dependencies:
            adj[dep].append(n.id)
            indeg[n.id] += 1

    q = deque([nid for nid, d in indeg.items() if d == 0])
    visited = 0
    while q:
        u = q.popleft()
        visited += 1
        for v in adj[u]:
            indeg[v] -= 1
            if indeg[v] == 0:
                q.append(v)
    if visited != len(nodes_by_id):
        errors.append("Plan contains a cycle (DAG invariant violated).")
    return errors


def validate_trace(trace: Trace, plan: Plan | None = None) -> list[str]:
    errors: list[str] = []

    if trace.schema_version not in SUPPORTED_TRACE_SCHEMA_VERSIONS:
        errors.append(
            f"Unsupported trace schema_version={trace.schema_version} "
            f"(supported: {sorted(SUPPORTED_TRACE_SCHEMA_VERSIONS)})"
        )
    if trace.runtime_protocol_version not in SUPPORTED_RUNTIME_PROTOCOL_VERSIONS:
        errors.append(
            f"Unsupported trace runtime_protocol_version={trace.runtime_protocol_version} "
            f"(supported: {sorted(SUPPORTED_RUNTIME_PROTOCOL_VERSIONS)})"
        )
    if trace.canonicalization_version not in SUPPORTED_CANONICALIZATION_VERSIONS:
        errors.append(
            f"Unsupported trace canonicalization_version={trace.canonicalization_version} "
            f"(supported: {sorted(SUPPORTED_CANONICALIZATION_VERSIONS)})"
        )
    if trace.fingerprint_algo not in SUPPORTED_FINGERPRINT_ALGOS:
        errors.append(
            f"Unsupported trace fingerprint_algo={trace.fingerprint_algo} "
            f"(supported: {sorted(SUPPORTED_FINGERPRINT_ALGOS)})"
        )
    plan_nodes: set[str] = set()
    if plan is not None:
        plan_nodes = {n.id for n in plan.nodes}

    for idx, ev in enumerate(trace.events):
        if ev.idx is None:
            errors.append("Trace event missing idx field")
        elif ev.idx != idx:
            errors.append("Trace idx must be monotonically increasing from 0")

    tool_calls: set[str] = set()
    tool_results: set[str] = set()
    evidence_ids: set[str] = set()

    started: set[str] = set()
    finished: set[str] = set()

    for ev in trace.events:
        if ev.kind == TraceEventKind.step_started:
            started.add(ev.step_id)
            if plan_nodes and ev.step_id not in plan_nodes:
                errors.append(f"step_started references unknown step {ev.step_id}")
        if ev.kind == TraceEventKind.step_finished:
            finished.add(ev.step_id)
        if ev.kind == TraceEventKind.tool_called:
            if ev.call.id in tool_calls:
                errors.append(f"Duplicate tool call id: {ev.call.id}")
            tool_calls.add(ev.call.id)
        if ev.kind == TraceEventKind.tool_returned:
            tool_results.add(ev.result.call_id)
            if ev.result.call_id not in tool_calls:
                errors.append(
                    f"ToolReturned references unknown call: {ev.result.call_id}"
                )
        if ev.kind == TraceEventKind.evidence_registered:
            if not ev.step_id:
                errors.append("Evidence event missing step_id")
            if ev.evidence.id in evidence_ids:
                errors.append(f"Duplicate evidence id: {ev.evidence.id}")
            evidence_ids.add(ev.evidence.id)

    missing = tool_calls - tool_results
    if missing:
        errors.append(f"Missing tool results for call ids: {sorted(missing)}")

    if started - finished:
        errors.append(f"Unfinished steps: {sorted(started - finished)}")

    # Evidence referenced by claims?
    claim_refs: set[str] = set()
    for ev in trace.events:
        if ev.kind == TraceEventKind.claim_emitted:
            for sup in ev.claim.supports:
                if sup.kind == "evidence":
                    claim_refs.add(sup.ref_id)
    return errors


def validate_verification_report(report: VerificationReport) -> list[str]:
    errors: list[str] = []
    seen: set[str] = set()
    for check in report.checks:
        if check.name in seen:
            errors.append(f"Duplicate check name: {check.name}")
        seen.add(check.name)
    return errors
