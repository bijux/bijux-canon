# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.core.fingerprints import stable_id
from bijux_rar.core.rar_types import JsonValue, Plan, PlanNode, ProblemSpec
from bijux_rar.rar.planning.ir import StepSpec, ToolRequest


def plan_problem(spec: ProblemSpec, preset: str) -> Plan:
    """
    Pure planner: ProblemSpec -> Plan.

    Deterministic decomposition:
      understand -> gather -> derive -> verify -> finalize

    Notes:
    - No I/O
    - No randomness
    - All IDs are content-addressed by core model validators.
    """
    spec = spec if spec.id else spec.with_content_id()
    steps: list[StepSpec] = _build_steps(spec=spec, preset=preset)
    nodes: list[PlanNode] = []

    prev_id: str | None = None
    for step in steps:
        deps = [] if prev_id is None else [prev_id]
        params = _step_params(step, preset=preset)
        node = PlanNode(
            id=stable_id("node", {"kind": step.kind, "deps": deps, "params": params}),
            kind=step.kind,
            dependencies=deps,
            step=step,
            parameters=params,
        )
        nodes.append(node)
        prev_id = node.id

    plan = Plan(problem=spec.description, spec_id=spec.id, nodes=nodes, edges=[])
    return plan.with_content_id()


def _build_steps(spec: ProblemSpec, preset: str) -> list[StepSpec]:
    constraints = spec.constraints or {}

    wants_retrieval = bool(constraints.get("needs_retrieval", False))

    gather_tools: list[ToolRequest] = []
    if wants_retrieval:
        raw_top_k = constraints.get("top_k", 3)
        top_k = int(raw_top_k) if isinstance(raw_top_k, (int, float, str)) else 3
        gather_tools.append(
            ToolRequest(
                tool_name="retrieve",
                arguments={
                    "query": constraints.get("query", spec.description),
                    "top_k": top_k,
                },
            )
        )

    return [
        StepSpec(kind="understand", notes="Normalize/understand the problem."),
        StepSpec(
            kind="gather", tool_requests=gather_tools, notes="Gather evidence/tools."
        ),
        StepSpec(kind="derive", notes="Derive candidate structured claim(s)."),
        StepSpec(kind="verify", notes="Verify internal consistency."),
        StepSpec(kind="finalize", notes="Finalize outputs."),
    ]


def _step_params(step: StepSpec, preset: str) -> dict[str, JsonValue]:
    return {
        "preset": preset,
    }
