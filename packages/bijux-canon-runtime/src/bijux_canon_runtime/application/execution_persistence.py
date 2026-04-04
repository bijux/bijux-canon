# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Persistence and resume helpers for runtime execution."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.application.flow_execution_models import (
    ExecutionConfig,
    FlowRunResult,
)
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.entropy_usage import EntropyUsage
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.observability.storage.execution_store_protocol import (
    ExecutionReadStoreProtocol,
)
from bijux_canon_runtime.ontology.ids import ClaimID, RunID, TenantID


@dataclass(frozen=True)
class ResumeState:
    """Resume state snapshot; misuse breaks crash recovery."""

    resume_from_step_index: int
    starting_event_index: int
    starting_evidence_index: int
    starting_tool_invocation_index: int
    starting_entropy_index: int
    events: tuple[ExecutionEvent, ...]
    artifacts: tuple[Artifact, ...]
    evidence: tuple[RetrievedEvidence, ...]
    tool_invocations: tuple[ToolInvocation, ...]
    entropy_usage: tuple[EntropyUsage, ...]
    claim_ids: tuple[ClaimID, ...]


def persist_run(result: FlowRunResult, config: ExecutionConfig) -> FlowRunResult:
    """Persist runtime execution outputs and return a normalized result record."""
    store = config.execution_store
    if store is None:
        raise ValueError("execution_store is required for persisted runs")
    plan = result.resolved_flow.plan
    run_id = result.run_id
    if run_id is None:
        store.register_dataset(plan.dataset)
        run_id = store.begin_run(plan=plan, mode=config.mode)
        store.save_steps(run_id=run_id, tenant_id=plan.tenant_id, plan=plan)
    if result.trace is not None:
        if config.mode in {RunMode.DRY_RUN, RunMode.OBSERVE}:
            store.save_events(
                run_id=run_id, tenant_id=plan.tenant_id, events=result.trace.events
            )
            store.append_tool_invocations(
                run_id=run_id,
                tenant_id=plan.tenant_id,
                tool_invocations=result.trace.tool_invocations,
                starting_index=0,
            )
            store.append_entropy_usage(
                run_id=run_id,
                usage=result.trace.entropy_usage,
                starting_index=0,
            )
            store.save_artifacts(run_id=run_id, artifacts=result.artifacts)
            store.append_evidence(
                run_id=run_id,
                evidence=result.evidence,
                starting_index=0,
            )
            store.append_claim_ids(
                run_id=run_id,
                tenant_id=plan.tenant_id,
                claim_ids=result.trace.claim_ids,
            )
        store.finalize_run(run_id=run_id, trace=result.trace)
    return FlowRunResult(
        resolved_flow=result.resolved_flow,
        trace=result.trace,
        artifacts=result.artifacts,
        evidence=result.evidence,
        reasoning_bundles=result.reasoning_bundles,
        verification_results=result.verification_results,
        verification_arbitrations=result.verification_arbitrations,
        run_id=run_id,
    )


def resolve_read_store(config: ExecutionConfig) -> ExecutionReadStoreProtocol:
    """Resolve the read store used for resumed execution."""
    if config.execution_read_store is not None:
        return config.execution_read_store
    if isinstance(config.execution_store, DuckDBExecutionWriteStore):
        return DuckDBExecutionReadStore(config.execution_store.path)
    raise ValueError("execution_read_store is required for resume")


def load_resume_state(
    store: ExecutionReadStoreProtocol,
    *,
    run_id: RunID,
    tenant_id: TenantID,
) -> ResumeState:
    """Load persisted resume state for a partially completed run."""
    events = store.load_events(run_id, tenant_id=tenant_id)
    artifacts = store.load_artifacts(run_id, tenant_id=tenant_id)
    evidence = store.load_evidence(run_id, tenant_id=tenant_id)
    tool_invocations = store.load_tool_invocations(run_id, tenant_id=tenant_id)
    entropy_usage = store.load_entropy_usage(run_id, tenant_id=tenant_id)
    claim_ids = store.load_claim_ids(run_id, tenant_id=tenant_id)
    checkpoint = store.load_checkpoint(run_id, tenant_id=tenant_id)
    resume_from_step_index = -1
    starting_event_index = 0
    if events:
        starting_event_index = events[-1].event_index + 1
        resume_from_step_index = max(
            (
                event.step_index
                for event in events
                if event.event_type.value == "STEP_END"
            ),
            default=resume_from_step_index,
        )
    if checkpoint is not None:
        resume_from_step_index = checkpoint[0]
        starting_event_index = max(starting_event_index, checkpoint[1] + 1)
    return ResumeState(
        resume_from_step_index=resume_from_step_index,
        starting_event_index=starting_event_index,
        starting_evidence_index=len(evidence),
        starting_tool_invocation_index=len(tool_invocations),
        starting_entropy_index=len(entropy_usage),
        events=events,
        artifacts=artifacts,
        evidence=evidence,
        tool_invocations=tool_invocations,
        entropy_usage=entropy_usage,
        claim_ids=claim_ids,
    )


__all__ = [
    "ResumeState",
    "load_resume_state",
    "persist_run",
    "resolve_read_store",
]
