# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass

from pydantic import TypeAdapter

from bijux_canon_reason.core.invariants import validate_plan
from bijux_canon_reason.core.types import (
    Plan,
    PlanNode,
    ProblemSpec,
    ToolResult,
    Trace,
    TraceEvent,
    TraceEventKind,
)
from bijux_canon_reason.execution.runtime import ExecutionRuntime
from bijux_canon_reason.execution.step_execution import (
    ExecutionState,
    build_step_output,
)
from bijux_canon_reason.execution.tool_dispatch import (
    ToolDispatchResult,
    dispatch_tool_requests,
)
from bijux_canon_reason.execution.trace_metadata import build_trace_result


@dataclass(frozen=True)
class ExecutionPolicy:
    fail_fast: bool = True
    min_supports_per_claim: int = 2


@dataclass(frozen=True)
class ExecutionResult:
    trace: Trace

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        return {"trace": self.trace.model_dump(mode=mode)}


@dataclass
class _EventLog:
    adapter: TypeAdapter[TraceEvent]
    events: list[TraceEvent]
    next_idx: int = 0

    def append(self, payload: dict[str, object]) -> None:
        payload["idx"] = self.next_idx
        self.next_idx += 1
        self.events.append(self.adapter.validate_python(payload))


def _validate_topology(plan: Plan) -> None:
    """Fail fast on topology violations before any execution starts."""
    nodes = {n.id for n in plan.nodes}
    # Edges (if provided) must reference existing nodes.
    for u, v in plan.edges:
        if u not in nodes or v not in nodes:
            raise RuntimeError(
                f"INV-ORD-001: edge references unknown node {(u, v)} in plan topology"
            )
    # Dependencies must point to existing nodes.
    for node in plan.nodes:
        for dep in node.dependencies:
            if dep not in nodes:
                raise RuntimeError(
                    f"INV-ORD-001: node {node.id} depends on missing node {dep}"
                )


def _topo(plan: Plan) -> list[PlanNode]:
    _validate_topology(plan)
    nodes = {n.id: n for n in plan.nodes}
    remaining = set(nodes.keys())
    resolved: set[str] = set()
    out: list[PlanNode] = []
    while remaining:
        progressed = False
        for nid in sorted(remaining):
            n = nodes[nid]
            if all(d in resolved for d in n.dependencies):
                out.append(n)
                resolved.add(nid)
                remaining.remove(nid)
                progressed = True
                break
        if not progressed:
            raise RuntimeError("INV-ORD-001: plan is not a DAG (cycle detected)")
    return out


def execute_plan(
    *,
    spec: ProblemSpec | None = None,
    plan: Plan,
    runtime: ExecutionRuntime,
    policy: ExecutionPolicy | None = None,
) -> ExecutionResult:
    policy = policy or ExecutionPolicy(fail_fast=True)
    spec = (
        spec or ProblemSpec(description=plan.problem, constraints={}).with_content_id()
    )
    plan = plan.with_content_id()
    plan_errors = validate_plan(plan)
    if plan_errors:
        raise ValueError("; ".join(plan_errors))

    events: list[TraceEvent] = []
    event_log = _EventLog(adapter=TypeAdapter(TraceEvent), events=events)
    state = ExecutionState()
    min_supports = _resolve_min_supports(spec=spec, policy=policy)

    for node in _topo(plan):
        _execute_node(
            node=node,
            spec=spec,
            runtime=runtime,
            state=state,
            min_supports=min_supports,
            policy=policy,
            event_log=event_log,
        )

    trace = build_trace_result(
        spec_id=spec.id,
        plan_id=plan.id,
        events=events,
        runtime=runtime,
        state=state,
        min_supports=min_supports,
    )

    return ExecutionResult(trace=trace)


def _resolve_min_supports(*, spec: ProblemSpec, policy: ExecutionPolicy) -> int:
    min_supports = policy.min_supports_per_claim
    if isinstance(spec.constraints, dict):
        raw_min = spec.constraints.get("min_supports_per_claim")
        if isinstance(raw_min, (int, float, str)):
            min_supports = max(1, int(raw_min))
    return min_supports


def _execute_node(
    *,
    node: PlanNode,
    spec: ProblemSpec,
    runtime: ExecutionRuntime,
    state: ExecutionState,
    min_supports: int,
    policy: ExecutionPolicy,
    event_log: _EventLog,
) -> None:
    event_log.append(
        {
            "kind": TraceEventKind.step_started,
            "step_id": node.id,
        }
    )
    tool_dispatch = dispatch_tool_requests(
        node_id=node.id,
        tool_requests=node.step.tool_requests,
        runtime=runtime,
        push_event=event_log.append,
    )
    _merge_tool_dispatch(state=state, tool_dispatch=tool_dispatch)
    _raise_on_tool_failures(
        node_id=node.id,
        policy=policy,
        failures=tool_dispatch.failures,
    )

    out = build_step_output(
        node=node,
        spec=spec,
        state=state,
        min_supports=min_supports,
    )
    if node.kind == "derive" and getattr(out, "claim_ids", None):
        claim_id = out.claim_ids[0]
        event_log.append(
            {
                "kind": TraceEventKind.claim_emitted,
                "step_id": node.id,
                "claim": state.claims[claim_id].model_dump(mode="json"),
            }
        )
    event_log.append(
        {
            "kind": TraceEventKind.step_finished,
            "step_id": node.id,
            "output": out.model_dump(mode="json"),
        }
    )


def _merge_tool_dispatch(
    *,
    state: ExecutionState,
    tool_dispatch: ToolDispatchResult,
) -> None:
    if tool_dispatch.retrieval_provenance:
        state.retrieval_provenance = tool_dispatch.retrieval_provenance
    for evidence_record in tool_dispatch.evidences:
        state.evidence_ids.append(evidence_record.reference.id)
        state.evidence_bytes[evidence_record.reference.id] = evidence_record.content


def _raise_on_tool_failures(
    *, node_id: str, policy: ExecutionPolicy, failures: list[ToolResult]
) -> None:
    if not failures or not policy.fail_fast:
        return
    first_failure = failures[0]
    detail = getattr(first_failure, "error", None) or "unknown tool error"
    raise RuntimeError(f"step {node_id} tool failure: {detail}")
