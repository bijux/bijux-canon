# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.observability.analysis.trace_diff import semantic_trace_diff
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

pytestmark = pytest.mark.regression


def test_probabilistic_replay_accepts_reordered_events() -> None:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("dataset-prob"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="hash-prob",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )
    event_one = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload={"event_type": EventType.STEP_START.value},
        payload_hash="hash-a",
    )
    event_two = ExecutionEvent(
        spec_version="v1",
        event_index=1,
        step_index=1,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:00:01Z",
        payload={"event_type": EventType.STEP_START.value},
        payload_hash="hash-b",
    )

    trace_one = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-prob"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.PROBABILISTIC,
        replay_acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
        dataset=dataset,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=0.5,
            max_contradiction_delta=1,
        ),
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(event_one, event_two),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    trace_two = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-prob"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.PROBABILISTIC,
        replay_acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
        dataset=dataset,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=0.5,
            max_contradiction_delta=1,
        ),
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(event_two, event_one),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )

    diff_prob = semantic_trace_diff(
        trace_one,
        trace_two,
        acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
    )
    assert diff_prob["acceptable_events"] == "different but acceptable under policy"
    assert diff_prob["non_determinism_report"]["expected_entropy"]["count"] == 0

    diff_strict = semantic_trace_diff(
        trace_one,
        trace_two,
        acceptability=ReplayAcceptability.EXACT_MATCH,
    )
    assert "events" in diff_strict
