# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

from agentic_flows.runtime.observability.analysis.trace_diff import (
    render_semantic_diff,
    semantic_trace_diff,
)
from agentic_flows.core.errors import NonDeterminismViolationError
from agentic_flows.spec.model.artifact.entropy_budget import EntropyBudget
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.non_deterministic_intent import (
    NonDeterministicIntent,
)
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.flow_manifest import FlowManifest
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.model.policy.non_determinism_policy import (
    NonDeterminismPolicy,
)
from agentic_flows.spec.ontology import (
    CausalityTag,
    DatasetState,
    DeterminismLevel,
    EntropyMagnitude,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    AgentID,
    ContractID,
    DatasetID,
    EnvironmentFingerprint,
    FlowID,
    GateID,
    PlanHash,
    ResolverID,
    TenantID,
)
from agentic_flows.spec.ontology.public import (
    EntropySource,
    EventType,
    NonDeterminismIntentSource,
    ReplayAcceptability,
    ReplayMode,
)


def build_manifest() -> FlowManifest:
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
    intents = (
        NonDeterministicIntent(
            spec_version="v1",
            source=NonDeterminismIntentSource.RETRIEVAL,
            min_entropy_magnitude=EntropyMagnitude.LOW,
            max_entropy_magnitude=EntropyMagnitude.MEDIUM,
            justification="retrieval ranking variance within bounds",
        ),
        NonDeterministicIntent(
            spec_version="v1",
            source=NonDeterminismIntentSource.LLM,
            min_entropy_magnitude=EntropyMagnitude.LOW,
            max_entropy_magnitude=EntropyMagnitude.MEDIUM,
            justification="bounded sampling for synthesis",
        ),
    )
    return FlowManifest(
        spec_version="v1",
        flow_id=FlowID("nondeterministic-flow"),
        tenant_id=TenantID("tenant-a"),
        flow_state=FlowState.VALIDATED,
        determinism_level=DeterminismLevel.BOUNDED,
        replay_acceptability=ReplayAcceptability.STATISTICALLY_BOUNDED,
        replay_mode=ReplayMode.BOUNDED,
        entropy_budget=EntropyBudget(
            spec_version="v1",
            allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
            max_magnitude=EntropyMagnitude.MEDIUM,
        ),
        allowed_variance_class=EntropyMagnitude.MEDIUM,
        nondeterminism_intent=intents,
        replay_envelope=ReplayEnvelope(
            spec_version="v1",
            min_claim_overlap=0.5,
            max_contradiction_delta=1,
        ),
        dataset=dataset,
        allow_deprecated_datasets=False,
        agents=(AgentID("agent-a"),),
        dependencies=(),
        retrieval_contracts=(ContractID("contract-a"),),
        verification_gates=(GateID("gate-a"),),
    )


def build_trace(manifest: FlowManifest, *, reverse_events: bool) -> ExecutionTrace:
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
    events = (event_two, event_one) if reverse_events else (event_one, event_two)
    return ExecutionTrace(
        spec_version="v1",
        flow_id=manifest.flow_id,
        tenant_id=manifest.tenant_id,
        parent_flow_id=None,
        child_flow_ids=(),
        flow_state=manifest.flow_state,
        determinism_level=manifest.determinism_level,
        replay_mode=manifest.replay_mode,
        replay_acceptability=manifest.replay_acceptability,
        dataset=manifest.dataset,
        replay_envelope=manifest.replay_envelope,
        allow_deprecated_datasets=manifest.allow_deprecated_datasets,
        environment_fingerprint=EnvironmentFingerprint("env"),
        plan_hash=PlanHash("plan"),
        verification_policy_fingerprint=None,
        resolver_id=ResolverID("resolver"),
        events=events,
        tool_invocations=(),
        entropy_usage=(),
        claim_ids=(),
        contradiction_count=0,
        arbitration_decision="none",
        finalized=True,
    )


def main() -> None:
    manifest = build_manifest()

    relaxed_policy = NonDeterminismPolicy(
        spec_version="v1",
        policy_id="relaxed",
        allowed_sources=(EntropySource.SEEDED_RNG, EntropySource.DATA),
        allowed_intent_sources=(
            NonDeterminismIntentSource.RETRIEVAL,
            NonDeterminismIntentSource.LLM,
        ),
        min_entropy_magnitude=EntropyMagnitude.LOW,
        max_entropy_magnitude=EntropyMagnitude.MEDIUM,
        allowed_variance_class=EntropyMagnitude.MEDIUM,
        require_justification=True,
    )
    strict_policy = NonDeterminismPolicy(
        spec_version="v1",
        policy_id="strict",
        allowed_sources=(EntropySource.SEEDED_RNG,),
        allowed_intent_sources=(NonDeterminismIntentSource.LLM,),
        min_entropy_magnitude=EntropyMagnitude.LOW,
        max_entropy_magnitude=EntropyMagnitude.LOW,
        allowed_variance_class=EntropyMagnitude.LOW,
        require_justification=True,
    )
    relaxed_policy.validate_intents(manifest.nondeterminism_intent)
    try:
        strict_policy.validate_intents(manifest.nondeterminism_intent)
    except NonDeterminismViolationError as exc:
        print(f"strict policy rejects intent: {exc}")

    expected = build_trace(manifest, reverse_events=False)
    observed = build_trace(manifest, reverse_events=True)
    diff = semantic_trace_diff(
        expected,
        observed,
        acceptability=manifest.replay_acceptability,
    )
    print(render_semantic_diff(diff))
    diff_strict = semantic_trace_diff(
        expected,
        observed,
        acceptability=ReplayAcceptability.EXACT_MATCH,
    )
    if "events" in diff_strict:
        print("strict replay rejected: event order mismatch")


if __name__ == "__main__":
    main()
