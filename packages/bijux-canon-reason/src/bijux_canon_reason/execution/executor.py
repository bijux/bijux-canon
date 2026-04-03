# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass

from pydantic import TypeAdapter

from bijux_canon_reason.core.invariants import validate_plan
from bijux_canon_reason.core.types import (
    Claim,
    ClaimStatus,
    ClaimType,
    DeriveOutput,
    EvidenceRef,
    FinalizeOutput,
    GatherOutput,
    InsufficientEvidenceOutput,
    JsonValue,
    Plan,
    PlanNode,
    ProblemSpec,
    StepOutput,
    SupportKind,
    SupportRef,
    Trace,
    TraceEvent,
    TraceEventKind,
    UnderstandOutput,
    VerifyOutput,
)
from bijux_canon_reason.execution.evidence_records import coerce_reasoner_value
from bijux_canon_reason.execution.runtime import Runtime
from bijux_canon_reason.execution.tool_dispatch import dispatch_tool_requests
from bijux_canon_reason.reasoning.backend import BaselineReasoner


@dataclass(frozen=True)
class ExecutionPolicy:
    fail_fast: bool = True
    min_supports_per_claim: int = 2


@dataclass(frozen=True)
class ExecutionResult:
    trace: Trace

    def model_dump(self, mode: str = "json") -> dict[str, object]:
        return {"trace": self.trace.model_dump(mode=mode)}
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
    runtime: Runtime,
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

    adapter: TypeAdapter[TraceEvent] = TypeAdapter(TraceEvent)
    events: list[TraceEvent] = []
    claims: dict[str, Claim] = {}
    evidence_ids: list[str] = []
    evidence_bytes: dict[str, bytes] = {}
    validated_claim_ids: list[str] = []
    rejected_claim_ids: list[str] = []
    missing_support_claim_ids: list[str] = []
    retrieval_provenance: dict[str, JsonValue] = {}
    reasoning_meta: dict[str, JsonValue] = {}
    min_supports = policy.min_supports_per_claim
    if isinstance(spec.constraints, dict):
        raw_min = spec.constraints.get("min_supports_per_claim")
        if isinstance(raw_min, (int, float, str)):
            min_supports = max(1, int(raw_min))

    idx_counter = 0

    def _push_event(payload: dict[str, object]) -> None:
        nonlocal idx_counter
        payload["idx"] = idx_counter
        idx_counter += 1
        events.append(adapter.validate_python(payload))

    for node in _topo(plan):
        events.append(
            adapter.validate_python(
                {
                    "kind": TraceEventKind.step_started,
                    "step_id": node.id,
                    "idx": idx_counter,
                }
            )
        )
        idx_counter += 1

        tool_dispatch = dispatch_tool_requests(
            node_id=node.id,
            tool_requests=node.step.tool_requests,
            runtime=runtime,
            push_event=_push_event,
        )
        if tool_dispatch.retrieval_provenance:
            retrieval_provenance = tool_dispatch.retrieval_provenance
        for evidence_record in tool_dispatch.evidences:
            evidence_ids.append(evidence_record.reference.id)
            evidence_bytes[evidence_record.reference.id] = evidence_record.content

        out: StepOutput | None = None
        if node.kind == "understand":
            out = UnderstandOutput(
                normalized_question=spec.description.strip(), assumptions=[]
            )

        elif node.kind == "gather":
            out = GatherOutput(
                evidence_ids=list(evidence_ids),
                retrieval_queries=[spec.description],
                retrieval_provenance=retrieval_provenance,
            )

        elif node.kind == "derive":
            ranked_evidence = [
                (eid, evidence_bytes.get(eid, b"")) for eid in evidence_ids
            ]
            available = [ev for ev in ranked_evidence if ev[1]]
            if len(available) < min_supports:
                out = InsufficientEvidenceOutput(
                    retrieved=len(available),
                    required=min_supports,
                )
            else:
                raw_max = (
                    spec.constraints.get("max_citations", min_supports)
                    if isinstance(spec.constraints, dict)
                    else min_supports
                )
                try:
                    max_citations = (
                        max(min_supports, int(raw_max))
                        if isinstance(raw_max, (int, float, str))
                        else min_supports
                    )
                except Exception:  # noqa: BLE001
                    max_citations = min_supports
                reasoner = BaselineReasoner()
                deriv = reasoner.derive(
                    question=spec.description,
                    evidence=ranked_evidence,
                    max_citations=max_citations,
                )
                supports = [
                    SupportRef(
                        kind=SupportKind.evidence,
                        ref_id=c.evidence_id,
                        span=c.span,
                        snippet_sha256=c.snippet_sha256,
                    )
                    for c in deriv.citations
                ]
                rr: dict[str, JsonValue] = {}
                if isinstance(deriv.raw_reasoner, dict):
                    for k, v_obj in deriv.raw_reasoner.items():
                        rr[str(k)] = coerce_reasoner_value(v_obj)

                claim = Claim(
                    id="",
                    statement=deriv.statement,
                    status=ClaimStatus.proposed,
                    confidence=0.7 if supports else 0.1,
                    supports=supports,
                    claim_type=ClaimType.derived,
                    structured={
                        "reasoner": rr,
                        "result_sha256": deriv.result_sha256,
                    },
                ).with_content_id()
                claims[claim.id] = claim
                _push_event(
                    {
                        "kind": TraceEventKind.claim_emitted,
                        "step_id": node.id,
                        "claim": claim.model_dump(mode="json"),
                    }
                )
                reason_meta_local = {
                    "question": spec.description,
                    "evidence_ids": [eid for eid, _ in ranked_evidence],
                    "result_sha256": deriv.result_sha256,
                }
                reasoning_meta.update(
                    {k: coerce_reasoner_value(v) for k, v in reason_meta_local.items()}
                )
                out = DeriveOutput(claim_ids=[claim.id])

        elif node.kind == "verify":
            for cid, c in claims.items():
                if c.claim_type == ClaimType.assumed or c.supports:
                    validated_claim_ids.append(cid)
                else:
                    missing_support_claim_ids.append(cid)
                    rejected_claim_ids.append(cid)
            out = VerifyOutput(
                validated_claim_ids=sorted(set(validated_claim_ids)),
                rejected_claim_ids=sorted(set(rejected_claim_ids)),
                missing_support_claim_ids=sorted(set(missing_support_claim_ids)),
            )

        elif node.kind == "finalize":
            final_ids = sorted(set(validated_claim_ids)) or sorted(claims.keys())
            answer = claims[final_ids[0]].statement if final_ids else None
            out = FinalizeOutput(
                final_claim_ids=final_ids,
                final_answer=answer,
                uncertainty=None if final_ids else "No validated claim",
            )

        else:
            raise RuntimeError(f"Unknown step kind: {node.kind}")

        _push_event(
            {
                "kind": TraceEventKind.step_finished,
                "step_id": node.id,
                "output": out.model_dump(mode="json"),
            }
        )

    trace = Trace(
        id="",
        spec_id=spec.id,
        plan_id=plan.id,
        events=events,
        metadata={
            "run_meta": {
                "seed": runtime.seed,
                "runtime_kind": runtime.runtime_kind,
                "mode": runtime.mode,
            }
        },
    ).with_content_id()
    meta_policy: dict[str, JsonValue] = {"min_supports_per_claim": min_supports}
    if reasoning_meta and "result_sha256" in reasoning_meta:
        reasoning_meta["reasoning_trace_sha256"] = str(reasoning_meta["result_sha256"])
    meta = dict(trace.metadata)
    meta["reasoning_policy"] = meta_policy
    if retrieval_provenance:
        meta["retrieval_provenance"] = retrieval_provenance
    if reasoning_meta:
        meta["reasoning_trace"] = reasoning_meta
    trace = trace.model_copy(update={"metadata": meta}).with_content_id()

    return ExecutionResult(trace=trace)
