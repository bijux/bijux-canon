# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import dataclasses

import pytest

from agentic_flows.runtime.observability.capture.trace_recorder import AppendOnlyList
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.ontology import (
    CausalityTag,
    DatasetState,
    DeterminismLevel,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    ResolverID,
    TenantID,
)
from agentic_flows.spec.ontology.public import (
    EventType,
    ReplayAcceptability,
)

pytestmark = pytest.mark.unit


def _build_trace() -> ExecutionTrace:
    events = AppendOnlyList()
    events.append(
        ExecutionEvent(
            spec_version="v1",
            event_index=0,
            step_index=0,
            event_type=EventType.STEP_START,
            causality_tag=CausalityTag.AGENT,
            timestamp_utc="1970-01-01T00:00:00Z",
            payload={"event_type": EventType.STEP_START.value},
            payload_hash="x",
        )
    )
    return ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-trace"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-trace"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash-trace",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env-fingerprint"),
        plan_hash=PlanHash("plan-hash"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("agentic-flows:v0"),
        events=tuple(events),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=False,
    )


def test_trace_is_immutable() -> None:
    trace = _build_trace()
    trace.finalize()

    with pytest.raises(dataclasses.FrozenInstanceError):
        trace.flow_id = "mutated"

    with pytest.raises(TypeError):
        trace.events[0] = ExecutionEvent(
            spec_version="v1",
            event_index=999,
            step_index=0,
            event_type=EventType.STEP_START,
            causality_tag=CausalityTag.AGENT,
            timestamp_utc="1970-01-01T00:00:00Z",
            payload={"event_type": EventType.STEP_START.value},
            payload_hash="x",
        )

    with pytest.raises(AttributeError):
        trace.events.pop()

    original_first = trace.events[0]
    with pytest.raises(AttributeError):
        trace.events.append(
            ExecutionEvent(
                spec_version="v1",
                event_index=999,
                step_index=0,
                event_type=EventType.STEP_END,
                causality_tag=CausalityTag.AGENT,
                timestamp_utc="1970-01-01T00:00:01Z",
                payload={"event_type": EventType.STEP_END.value},
                payload_hash="y",
            )
        )
    assert trace.events[0] == original_first


def test_trace_mutation_after_finalize_raises() -> None:
    trace = _build_trace()
    trace.finalize()
    with pytest.raises(dataclasses.FrozenInstanceError):
        trace.events = ()


def test_trace_mutation_after_finalize_attribute_raises() -> None:
    trace = _build_trace()
    trace.finalize()
    with pytest.raises(dataclasses.FrozenInstanceError):
        trace.arbitration_decision = "mutated"
