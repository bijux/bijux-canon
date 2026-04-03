# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.runtime.orchestration.planner import ExecutionPlanner
from agentic_flows.runtime.orchestration.replay_store import replay_with_store
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.ontology import (
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    FlowID,
    GateID,
    TenantID,
)
from agentic_flows.spec.ontology.public import EntropySource, ReplayAcceptability


def build_manifest() -> FlowManifest:
    """Build a minimal deterministic manifest for a single-step flow."""
    dataset_path = (
        Path(__file__).resolve().parents[1] / "datasets" / "retrieval_corpus.jsonl"
    )
    dataset = DatasetDescriptor(
        spec_version="v1",
        dataset_id=DatasetID("retrieval_corpus"),
        tenant_id=TenantID("tenant-a"),
        dataset_version="1.0.0",
        dataset_hash="136275faf776ff9aae3823d7d6f928e9",
        dataset_state=DatasetState.FROZEN,
        storage_uri=f"file://{dataset_path}",
    )
    return FlowManifest(
        spec_version="v1",
        flow_id=FlowID("minimal-flow"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG,),
            max_magnitude=EntropyMagnitude.LOW,
        ),
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


def main() -> None:
    """Run, persist, replay, and diff a deterministic flow."""
    manifest = build_manifest()
    db_path = Path(__file__).with_suffix(".duckdb")
    store = DuckDBExecutionWriteStore(db_path)

    run_config = ExecutionConfig(
        mode=RunMode.DRY_RUN,
        determinism_level=manifest.determinism_level,
        execution_store=store,
    )
    run_result = execute_flow(manifest=manifest, config=run_config)
    if run_result.run_id is None:
        raise RuntimeError("run_id missing from execution result")

    resolved_flow = ExecutionPlanner().resolve(manifest)
    read_store = DuckDBExecutionReadStore(db_path)
    replay_config = ExecutionConfig(
        mode=RunMode.DRY_RUN,
        determinism_level=manifest.determinism_level,
        execution_store=store,
    )
    diff, _ = replay_with_store(
        store=read_store,
        run_id=run_result.run_id,
        tenant_id=manifest.tenant_id,
        resolved_flow=resolved_flow,
        config=replay_config,
    )
    if diff:
        raise RuntimeError(f"replay diff detected: {diff}")


if __name__ == "__main__":
    main()
