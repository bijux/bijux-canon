# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.observability.analysis.flow_correlation import (
    validate_flow_correlation,
)
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.ontology import (
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
from agentic_flows.spec.ontology.public import ReplayAcceptability


def test_flow_correlation_requires_parent() -> None:
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
    parent = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("parent"),
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
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    child = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("child"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=FlowID("parent"),
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
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    validate_flow_correlation(child, [parent])


def test_flow_correlation_rejects_missing_parent() -> None:
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
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("child"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=FlowID("parent"),
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
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    with pytest.raises(ValueError, match="parent_flow_id"):
        validate_flow_correlation(trace, [])
