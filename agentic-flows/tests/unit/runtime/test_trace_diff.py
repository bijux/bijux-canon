# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from agentic_flows.runtime.observability.analysis.trace_diff import semantic_trace_diff
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.ontology import (
    CausalityTag,
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    ContentHash,
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    ResolverID,
    TenantID,
    ToolID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    EventType,
    ReplayAcceptability,
)


def test_semantic_trace_diff_ignores_timestamps() -> None:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("dataset"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="hash",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )
    replay_envelope = ReplayEnvelope(
        spec_version="v1",
        min_claim_overlap=1.0,
        max_contradiction_delta=0,
    )
    event_payload = {"event_type": EventType.STEP_START.value}
    event_one = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload=event_payload,
        payload_hash="hash",
    )
    event_two = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:01:00Z",
        payload=event_payload,
        payload_hash="hash",
    )
    trace_one = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-a"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=dataset,
        replay_envelope=replay_envelope,
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(event_one,),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    trace_two = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-a"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=dataset,
        replay_envelope=replay_envelope,
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(event_two,),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    assert semantic_trace_diff(trace_one, trace_two) == {}


def test_non_determinism_report_includes_class_taxonomy() -> None:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("dataset"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="hash",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )
    replay_envelope = ReplayEnvelope(
        spec_version="v1",
        min_claim_overlap=1.0,
        max_contradiction_delta=0,
    )
    event_payload = {"event_type": EventType.HUMAN_INTERVENTION.value}
    event = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.HUMAN_INTERVENTION,
        causality_tag=CausalityTag.HUMAN,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload=event_payload,
        payload_hash="hash",
    )
    tool_invocation = ToolInvocation(
        spec_version="v1",
        tool_id=ToolID("tool-x"),
        determinism_level=DeterminismLevel.BOUNDED,
        inputs_fingerprint=ContentHash("input-hash"),
        outputs_fingerprint=None,
        duration=0.1,
        outcome="ok",
    )
    entropy = EntropyUsage(
        spec_version="v1",
        tenant_id=TenantID("tenant-a"),
        source=EntropySource.SEEDED_RNG,
        magnitude=EntropyMagnitude.LOW,
        description="seeded",
        step_index=0,
        nondeterminism_source=NonDeterminismSource(
            source=EntropySource.SEEDED_RNG,
            authorized=True,
            scope=FlowID("flow-a"),
        ),
    )
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-a"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.PROBABILISTIC,
        replay_acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
        dataset=dataset,
        replay_envelope=replay_envelope,
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(event,),
        tool_invocations=(tool_invocation,),
        entropy_usage=(entropy,),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    diff = semantic_trace_diff(
        trace,
        trace,
        acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
    )
    report = diff["non_determinism_report"]["determinism_classes"]
    for label in ("structural", "environmental", "stochastic", "human", "external"):
        assert label in report["expected"]
