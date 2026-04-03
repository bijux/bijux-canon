# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.core.authority import enforce_runtime_semantics, finalize_trace
from bijux_canon_runtime.core.errors import SemanticViolationError
from bijux_canon_runtime.runtime.observability.capture.trace_recorder import TraceRecorder
from bijux_canon_runtime.model.datasets.dataset_descriptor import DatasetDescriptor
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.execution.replay_envelope import ReplayEnvelope
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.spec.ontology import (
    CausalityTag,
    DatasetState,
    DeterminismLevel,
    FlowState,
)
from bijux_canon_runtime.spec.ontology.ids import (
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    ResolverID,
    TenantID,
)
from bijux_canon_runtime.spec.ontology.public import (
    EventType,
    ReplayAcceptability,
)

pytestmark = pytest.mark.unit


def test_finalize_trace_twice_rejected() -> None:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("dataset"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="hash",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
    )
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=dataset,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=False,
    )

    finalize_trace(trace)
    with pytest.raises(SemanticViolationError):
        finalize_trace(trace)


def test_emit_event_without_authority_fails() -> None:
    recorder = TraceRecorder()
    event = ExecutionEvent(
        spec_version="v1",
        event_index=0,
        step_index=0,
        event_type=EventType.STEP_START,
        causality_tag=CausalityTag.AGENT,
        timestamp_utc="1970-01-01T00:00:00Z",
        payload={"event_type": EventType.STEP_START.value},
        payload_hash="payload",
    )
    with pytest.raises(TypeError):
        recorder.record(event, authority=None)  # type: ignore[arg-type]


def test_bypass_verification_is_rejected() -> None:
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("dataset"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="hash",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://examples/datasets/retrieval_corpus.jsonl",
    )
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=dataset,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )

    class _Result:
        def __init__(self) -> None:
            self.trace = trace
            self.verification_results = ()
            self.verification_arbitrations = ()
            self.reasoning_bundles = (object(),)

    with pytest.raises(SemanticViolationError):
        enforce_runtime_semantics(_Result(), mode="live")
