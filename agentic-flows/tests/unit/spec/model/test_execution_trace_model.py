# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

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

pytestmark = pytest.mark.unit


def test_trace_access_before_finalize_raises() -> None:
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-misuse"),
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
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan-hash"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("agentic-flows:v0"),
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=False,
    )

    with pytest.raises(
        RuntimeError, match="ExecutionTrace accessed before finalization"
    ):
        _ = trace.flow_id
