# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.determinism_guard import validate_replay
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
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
    EntropySource,
    ReplayAcceptability,
)

pytestmark = pytest.mark.regression


def test_dataset_mismatch_blocks_replay() -> None:
    plan = ExecutionSteps(
        spec_version="v1",
        flow_id=FlowID("flow-dataset"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
            max_magnitude=EntropyMagnitude.LOW,
        ),
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=1.0,
            max_contradiction_delta=0,
        ),
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-a"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash-a",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        steps=(),
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
    )
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-dataset"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-b"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash-b",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        replay_envelope=plan.replay_envelope,
        allow_deprecated_datasets=False,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("agentic-flows:v0"),
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )
    with pytest.raises(ValueError, match="dataset"):
        validate_replay(trace, plan)
