# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import sys
import types
from pathlib import Path

import pytest

from agentic_flows.runtime.artifact_store import InMemoryArtifactStore
from agentic_flows.runtime.observability.capture.environment import (
    compute_environment_fingerprint,
)
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.agent_invocation import AgentInvocation
from agentic_flows.spec.model.verification.arbitration_policy import ArbitrationPolicy
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.ontology import (
    ArbitrationRule,
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
    StepType,
    VerificationRandomness,
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
    ReplayAcceptability,
    ReplayMode,
)


def pytest_configure() -> None:
    if "bijux_cli" not in sys.modules:
        stub = types.ModuleType("bijux_cli")
        stub.__version__ = "0.0.0"
        sys.modules["bijux_cli"] = stub
    if "bijux_agent" not in sys.modules:
        stub = types.ModuleType("bijux_agent")
        stub.__version__ = "0.0.0"
        stub.run = lambda **_kwargs: []
        sys.modules["bijux_agent"] = stub
    if "bijux_rag" not in sys.modules:
        stub = types.ModuleType("bijux_rag")
        stub.retrieve = lambda **_kwargs: []
        sys.modules["bijux_rag"] = stub
    if "bijux_vex" not in sys.modules:
        stub = types.ModuleType("bijux_vex")
        stub.enforce_contract = lambda *_args, **_kwargs: True
        sys.modules["bijux_vex"] = stub
    if "bijux_rar" not in sys.modules:
        stub = types.ModuleType("bijux_rar")
        stub.reason = lambda **_kwargs: None
        sys.modules["bijux_rar"] = stub


@pytest.fixture(autouse=True)
def _stable_bijux_versions(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "agentic_flows.runtime.orchestration.planner.ExecutionPlanner._bijux_cli_version",
        "0.0.0",
        raising=False,
    )
    monkeypatch.setattr(
        "agentic_flows.runtime.orchestration.planner.ExecutionPlanner._bijux_agent_version",
        "0.0.0",
        raising=False,
    )


@pytest.fixture
def baseline_policy() -> VerificationPolicy:
    return VerificationPolicy(
        spec_version="v1",
        verification_level="baseline",
        failure_mode="halt",
        randomness_tolerance=VerificationRandomness.DETERMINISTIC,
        arbitration_policy=ArbitrationPolicy(
            spec_version="v1",
            rule=ArbitrationRule.UNANIMOUS,
            quorum_threshold=None,
        ),
        required_evidence=(),
        max_rule_cost=100,
        rules=(),
        fail_on=(),
        escalate_on=(),
    )


@pytest.fixture
def artifact_store() -> InMemoryArtifactStore:
    return InMemoryArtifactStore()


@pytest.fixture
def entropy_budget() -> EntropyBudget:
    return EntropyBudget(
        spec_version="v1",
        allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
        max_magnitude=EntropyMagnitude.LOW,
    )


@pytest.fixture
def replay_envelope() -> ReplayEnvelope:
    return ReplayEnvelope(
        spec_version="v1",
        min_claim_overlap=0.8,
        max_contradiction_delta=0,
    )


@pytest.fixture
def dataset_descriptor() -> DatasetDescriptor:
    return DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("retrieval_corpus"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="136275faf776ff9aae3823d7d6f928e9",
        dataset_state=DatasetState.FROZEN,
        storage_uri="file://datasets/retrieval_corpus.jsonl",
    )


@pytest.fixture
def tenant_id() -> TenantID:
    return TenantID("tenant-a")


@pytest.fixture
def deterministic_environment(
    monkeypatch: pytest.MonkeyPatch,
) -> EnvironmentFingerprint:
    fingerprint = EnvironmentFingerprint("env-fingerprint")
    monkeypatch.setattr(
        "agentic_flows.runtime.observability.capture.environment.compute_environment_fingerprint",
        lambda: fingerprint,
    )
    monkeypatch.setattr(
        "agentic_flows.runtime.orchestration.planner.compute_environment_fingerprint",
        lambda: fingerprint,
    )
    monkeypatch.setattr(
        "agentic_flows.runtime.orchestration.determinism_guard.compute_environment_fingerprint",
        lambda: fingerprint,
    )
    return fingerprint


@pytest.fixture
def execution_store(tmp_path: Path) -> DuckDBExecutionWriteStore:
    return DuckDBExecutionWriteStore(tmp_path / "execution.duckdb")


@pytest.fixture
def execution_read_store(tmp_path: Path) -> DuckDBExecutionReadStore:
    return DuckDBExecutionReadStore(tmp_path / "execution.duckdb")


@pytest.fixture
def plan_hash_for():
    def _plan_hash_for(
        flow_id: str,
        tenant_id: str,
        flow_state: FlowState,
        steps: tuple[ResolvedStep, ...],
        dependencies: dict[str, list[str]],
        *,
        determinism_level: DeterminismLevel,
        replay_acceptability: ReplayAcceptability,
        entropy_budget: EntropyBudget,
        replay_envelope: ReplayEnvelope,
        dataset,
        allow_deprecated_datasets: bool,
        replay_mode: ReplayMode = ReplayMode.STRICT,
        allowed_variance_class: EntropyMagnitude | None = None,
        nondeterminism_intent: tuple[NonDeterministicIntent, ...] = (),
    ) -> PlanHash:
        payload = {
            "flow_id": flow_id,
            "tenant_id": tenant_id,
            "flow_state": flow_state,
            "determinism_level": determinism_level,
            "replay_mode": replay_mode,
            "replay_acceptability": replay_acceptability,
            "entropy_budget": {
                "allowed_sources": list(entropy_budget.allowed_sources),
                "min_magnitude": entropy_budget.min_magnitude,
                "max_magnitude": entropy_budget.max_magnitude,
                "exhaustion_action": entropy_budget.exhaustion_action,
                "per_source": [
                    {
                        "source": entry.source,
                        "min_magnitude": entry.min_magnitude,
                        "max_magnitude": entry.max_magnitude,
                        "exhaustion_action": entry.exhaustion_action,
                    }
                    for entry in entropy_budget.per_source
                ],
            },
            "allowed_variance_class": allowed_variance_class,
            "nondeterminism_intent": [
                {
                    "source": intent.source,
                    "min_entropy_magnitude": intent.min_entropy_magnitude,
                    "max_entropy_magnitude": intent.max_entropy_magnitude,
                    "justification": intent.justification,
                }
                for intent in nondeterminism_intent
            ],
            "replay_envelope": {
                "min_claim_overlap": replay_envelope.min_claim_overlap,
                "max_contradiction_delta": replay_envelope.max_contradiction_delta,
            },
            "dataset": {
                "dataset_id": getattr(dataset, "dataset_id", None),
                "tenant_id": getattr(dataset, "tenant_id", None),
                "dataset_version": getattr(dataset, "dataset_version", None),
                "dataset_hash": getattr(dataset, "dataset_hash", None),
                "dataset_state": getattr(dataset, "dataset_state", None),
            },
            "allow_deprecated_datasets": allow_deprecated_datasets,
            "steps": [
                {
                    "index": step.step_index,
                    "agent_id": step.agent_id,
                    "inputs_fingerprint": step.inputs_fingerprint,
                    "declared_dependencies": list(step.declared_dependencies),
                    "step_type": step.step_type,
                    "determinism_level": step.determinism_level,
                    "declared_entropy_budget": (
                        {
                            "allowed_sources": list(
                                step.declared_entropy_budget.allowed_sources
                            ),
                            "min_magnitude": step.declared_entropy_budget.min_magnitude,
                            "max_magnitude": step.declared_entropy_budget.max_magnitude,
                            "exhaustion_action": step.declared_entropy_budget.exhaustion_action,
                            "per_source": [
                                {
                                    "source": entry.source,
                                    "min_magnitude": entry.min_magnitude,
                                    "max_magnitude": entry.max_magnitude,
                                    "exhaustion_action": entry.exhaustion_action,
                                }
                                for entry in step.declared_entropy_budget.per_source
                            ],
                        }
                        if step.declared_entropy_budget
                        else None
                    ),
                    "allowed_variance_class": step.allowed_variance_class,
                    "nondeterminism_intent": [
                        {
                            "source": intent.source,
                            "min_entropy_magnitude": intent.min_entropy_magnitude,
                            "max_entropy_magnitude": intent.max_entropy_magnitude,
                            "justification": intent.justification,
                        }
                        for intent in step.nondeterminism_intent
                    ],
                }
                for step in steps
            ],
            "dependencies": {
                agent_id: sorted(deps) for agent_id, deps in dependencies.items()
            },
        }
        return PlanHash(fingerprint_inputs(payload))

    return _plan_hash_for


@pytest.fixture
def resolved_flow(
    deterministic_environment,
    plan_hash_for,
    entropy_budget,
    replay_envelope,
    dataset_descriptor,
    tenant_id,
) -> ExecutionPlan:
    step = ResolvedStep(
        spec_version="v1",
        step_index=0,
        step_type=StepType.AGENT,
        determinism_level=DeterminismLevel.STRICT,
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
    )
    manifest = FlowManifest(
        spec_version="v1",
        flow_id=FlowID("flow-fixture"),
        tenant_id=tenant_id,
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )
    plan = ExecutionSteps(
        spec_version="v1",
        flow_id=FlowID("flow-fixture"),
        tenant_id=tenant_id,
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=entropy_budget,
        replay_envelope=replay_envelope,
        dataset=dataset_descriptor,
        allow_deprecated_datasets=False,
        steps=(step,),
        environment_fingerprint=deterministic_environment,
        plan_hash=plan_hash_for(
            "flow-fixture",
            str(tenant_id),
            FlowState.VALIDATED,
            (step,),
            {},
            determinism_level=manifest.determinism_level,
            replay_acceptability=manifest.replay_acceptability,
            entropy_budget=manifest.entropy_budget,
            replay_envelope=manifest.replay_envelope,
            dataset=manifest.dataset,
            allow_deprecated_datasets=manifest.allow_deprecated_datasets,
        ),
        resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
    )
    return ExecutionPlan(spec_version="v1", manifest=manifest, plan=plan)


@pytest.fixture
def resolved_flow_factory(plan_hash_for, entropy_budget):
    def _factory(
        manifest: FlowManifest,
        steps: tuple[ResolvedStep, ...],
        *,
        environment_fingerprint: EnvironmentFingerprint | None = None,
        dependencies: dict[str, list[str]] | None = None,
    ) -> ExecutionPlan:
        fingerprint = environment_fingerprint or EnvironmentFingerprint(
            compute_environment_fingerprint()
        )
        deps = dependencies or {}
        plan = ExecutionSteps(
            spec_version="v1",
            flow_id=FlowID(manifest.flow_id),
            tenant_id=manifest.tenant_id,
            flow_state=manifest.flow_state,
            determinism_level=manifest.determinism_level,
            replay_acceptability=manifest.replay_acceptability,
            entropy_budget=manifest.entropy_budget,
            replay_envelope=manifest.replay_envelope,
            dataset=manifest.dataset,
            allow_deprecated_datasets=manifest.allow_deprecated_datasets,
            steps=steps,
            environment_fingerprint=fingerprint,
            plan_hash=plan_hash_for(
                manifest.flow_id,
                str(manifest.tenant_id),
                manifest.flow_state,
                steps,
                deps,
                determinism_level=manifest.determinism_level,
                replay_acceptability=manifest.replay_acceptability,
                entropy_budget=manifest.entropy_budget,
                replay_envelope=manifest.replay_envelope,
                dataset=manifest.dataset,
                allow_deprecated_datasets=manifest.allow_deprecated_datasets,
            ),
            resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
        )
        return ExecutionPlan(spec_version="v1", manifest=manifest, plan=plan)

    return _factory
