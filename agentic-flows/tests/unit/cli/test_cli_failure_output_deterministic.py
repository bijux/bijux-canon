# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import argparse
import json
from pathlib import Path

from agentic_flows.cli import main as cli_main
from agentic_flows.core.authority import finalize_trace
from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from agentic_flows.runtime.orchestration.execute_flow import RunMode
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.ontology import (
    CausalityTag,
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
    EventType,
    ReplayAcceptability,
)


def _plan() -> ExecutionSteps:
    return ExecutionSteps(
        spec_version="v1",
        flow_id=FlowID("flow-cli-failure"),
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
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-cli-failure"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash-cli-failure",
            dataset_state=DatasetState.FROZEN,
            storage_uri="file://datasets/retrieval_corpus.jsonl",
        ),
        allow_deprecated_datasets=False,
        steps=(),
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan-hash"),
        resolution_metadata=(("resolver_id", ResolverID("agentic-flows:v0")),),
    )


def _trace() -> ExecutionTrace:
    event_payload = {"error": "boom", "timestamp_utc": "2020-01-01T00:00:00Z"}
    trace = ExecutionTrace(
        spec_version="v1",
        flow_id=FlowID("flow-cli-failure"),
        tenant_id=TenantID("tenant-a"),
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.STRICT,
        replay_acceptability=ReplayAcceptability.EXACT_MATCH,
        dataset=DatasetDescriptor(
            spec_version="v1",
            dataset_id=DatasetID("dataset-cli-failure"),
            tenant_id=TenantID("tenant-a"),
            dataset_version="1.0.0",
            dataset_hash="hash-cli-failure",
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
        events=(
            ExecutionEvent(
                spec_version="v1",
                event_index=0,
                step_index=0,
                event_type=EventType.STEP_FAILED,
                causality_tag=CausalityTag.AGENT,
                timestamp_utc="2020-01-01T00:00:00Z",
                payload=event_payload,
                payload_hash="payload-hash",
            ),
        ),
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=False,
    )
    finalize_trace(trace)
    return trace


def test_failure_output_is_deterministic(tmp_path: Path, capsys) -> None:
    db_path = tmp_path / "cli_failure.duckdb"
    store = DuckDBExecutionWriteStore(db_path)
    run_id = store.save_run(trace=_trace(), plan=_plan(), mode=RunMode.DRY_RUN)

    args = argparse.Namespace(
        run_id=str(run_id),
        tenant_id="tenant-a",
        db_path=str(db_path),
    )

    cli_main._explain_failure(args, json_output=True)
    first = capsys.readouterr().out.strip()
    cli_main._explain_failure(args, json_output=True)
    second = capsys.readouterr().out.strip()

    assert first == second
    payload = json.loads(first)
    assert payload["failure"]["timestamp_utc"] == "normalized"
