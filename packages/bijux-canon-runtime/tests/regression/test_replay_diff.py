# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.application.determinism_guard import validate_replay
from bijux_canon_runtime.application.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.entropy_budget import EntropyBudget
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.ontology import (
    ArtifactScope,
    ArtifactType,
    DeterminismLevel,
    EntropyMagnitude,
    EvidenceDeterminism,
    FlowState,
)
from bijux_canon_runtime.ontology.ids import (
    AgentID,
    ArtifactID,
    ContentHash,
    ContractID,
    EvidenceID,
    FlowID,
    GateID,
    PlanHash,
    ResolverID,
    TenantID,
)
from bijux_canon_runtime.ontology.public import (
    EntropySource,
    ReplayAcceptability,
)

pytestmark = pytest.mark.regression


def test_replay_diff_includes_artifacts_and_evidence(
    deterministic_environment, replay_envelope, dataset_descriptor
) -> None:
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-replay-diff"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
            max_magnitude=EntropyMagnitude.LOW,
        ),
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("alpha"),),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    result = execute_flow(
        manifest,
        config=ExecutionConfig(
            mode=RunMode.PLAN, determinism_level=manifest.determinism_level
        ),
    )
    plan = result.resolved_flow.plan

    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=plan.flow_id,
        tenant_id=plan.tenant_id,
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=plan.flow_state,
        determinism_level=plan.determinism_level,
        replay_acceptability=plan.replay_acceptability,
        dataset=plan.dataset,
        replay_envelope=plan.replay_envelope,
        allow_deprecated_datasets=plan.allow_deprecated_datasets,
        environment_fingerprint=plan.environment_fingerprint,
        plan_hash=PlanHash("mismatch"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("bijux-canon-runtime:v1"),
        events=(),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=False,
    )
    trace.finalize()

    artifacts = [
        Artifact(
            spec_version="v1",
            artifact_id=ArtifactID("artifact-1"),
            tenant_id=TenantID("tenant-a"),
            artifact_type=ArtifactType.AGENT_INVOCATION,
            producer="agent",
            parent_artifacts=(),
            content_hash=ContentHash("hash-1"),
            scope=ArtifactScope.WORKING,
        )
    ]
    evidence = [
        RetrievedEvidence(
            spec_version="v1",
            evidence_id=EvidenceID("ev-1"),
            tenant_id=TenantID("tenant-a"),
            determinism=EvidenceDeterminism.DETERMINISTIC,
            source_uri="file://doc",
            content_hash=ContentHash("hash-ev"),
            score=0.9,
            vector_contract_id=ContractID("contract-a"),
        )
    ]

    with pytest.raises(ValueError, match="artifact_fingerprint"):
        validate_replay(trace, plan, artifacts=artifacts, evidence=evidence)
