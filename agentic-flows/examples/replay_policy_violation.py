# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from agentic_flows.runtime.orchestration.determinism_guard import validate_replay
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.ontology import (
    CausalityTag,
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
    StepType,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    GateID,
    InputsFingerprint,
    PlanHash,
    ResolverID,
    TenantID,
    VersionID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    EventType,
    ReplayAcceptability,
    ReplayMode,
)


def build_plan() -> tuple[FlowManifest, ExecutionSteps]:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("retrieval_corpus"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="136275faf776ff9aae3823d7d6f928e9",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )
    budget = EntropyBudget(
        spec_version="v1",
        allowed_sources=(EntropySource.SEEDED_RNG,),
        max_magnitude=EntropyMagnitude.LOW,
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("replay-policy-violation"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        replay_mode=ReplayMode.STRICT,
        entropy_budget=budget,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=dataset,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    step = ResolvedStep(
        spec_version="v1",
        step_index=0,
        step_type=StepType.AGENT,
        determinism_level=manifest.determinism_level,
        agent_id=AgentID("agent-a"),
        inputs_fingerprint=InputsFingerprint("inputs"),
        declared_dependencies=(),
        expected_artifacts=(),
        agent_invocation=AgentInvocation(
            spec_version="v1",
            agent_id=AgentID("agent-a"),
            agent_version=VersionID("0.0.0"),
            inputs_fingerprint=InputsFingerprint("inputs"),
            declared_outputs=(),
            execution_mode="seeded",
        ),
        retrieval_request=None,
        declared_entropy_budget=budget,
    )
    plan = ExecutionSteps(
        spec_version="v1",
        flow_id=manifest.flow_id,
        tenant_id=manifest.tenant_id,
        flow_state=manifest.flow_state,
        determinism_level=manifest.determinism_level,
        replay_mode=manifest.replay_mode,
        replay_acceptability=manifest.replay_acceptability,
        entropy_budget=budget,
        replay_envelope=manifest.replay_envelope,
        dataset=manifest.dataset,
        allow_deprecated_datasets=manifest.allow_deprecated_datasets,
        steps=(step,),
        environment_fingerprint=EnvironmentFingerprint("env-plan"),
        plan_hash=PlanHash("plan-hash"),
        resolution_metadata=(("resolver_id", ResolverID("example")),),
    )
    return manifest, plan


def build_trace(manifest: FlowManifest) -> ExecutionTrace:
    event = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload={"event_type": EventType.STEP_START.value},
        payload_hash="hash",
    )
    return ExecutionTrace(
        spec_version="v1",
        flow_id=manifest.flow_id,
        tenant_id=manifest.tenant_id,
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=manifest.flow_state,
        determinism_level=manifest.determinism_level,
        replay_mode=manifest.replay_mode,
        replay_acceptability=manifest.replay_acceptability,
        dataset=manifest.dataset,
        replay_envelope=manifest.replay_envelope,
        allow_deprecated_datasets=manifest.allow_deprecated_datasets,
        environment_fingerprint=EnvironmentFingerprint("env-run"),
        plan_hash=PlanHash("plan-hash"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("example"),
        events=(event,),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )


def main() -> None:
    manifest, plan = build_plan()
    trace = build_trace(manifest)
    print("run completed; replaying against strict policy")
    try:
        validate_replay(trace, plan)
    except ValueError as exc:
        print(f"replay rejected: {exc}")


if __name__ == "__main__":
    main()
