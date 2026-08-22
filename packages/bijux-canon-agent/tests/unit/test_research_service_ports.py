from __future__ import annotations

import hashlib
import inspect
import json

from pydantic import ValidationError
import pytest

from bijux_canon_agent.application import (
    InjectedResearchServices,
    BudgetAction,
    BudgetDimensions,
    CancellationSignal,
    PolicyEnforcedResearchServices,
    ResearchOperation,
    ResearchRole,
    ResearchRoleMachine,
    ResearchBudgetPolicy,
    ResearchBudgetLedger,
    ResearchCheckpoint,
    ResearchFailureKind,
    ToolPolicyDenied,
)
from bijux_canon_agent.contracts import (
    ReasoningPortResult,
    ResearchPlanningInput,
    RetrievalPortResult,
    ServicePortDescriptor,
    ResearchTool,
    ResearchToolOperation,
    ToolGrant,
    ToolInvocation,
    ToolPolicy,
    ToolPolicyAction,
    ToolPolicyReason,
    plan_sha256,
)


def planning_input() -> ResearchPlanningInput:
    return ResearchPlanningInput(
        query="Which ancient-DNA extraction methods are reported?",
        corpus_generation="corpus-generation-1",
        index_generation="index-generation-1",
        scope=("source:one", "source:two"),
        top_k=2,
        retrieval_mode="lexical",
        constraints={"require_exact_citations": True},
        provider_profile={
            "provider": "bijux",
            "model": "baseline-extractive",
            "immutable_revision": "0.3.10",
            "temperature": 0.0,
            "seed": 17,
        },
        budget={
            "iterations": 8,
            "retrievals": 1,
            "candidates": 4,
            "evidence_items": 2,
            "tool_calls": 1,
            "provider_calls": 1,
            "tokens": 512,
            "elapsed_ms": 30000,
            "retries": 0,
            "artifact_bytes": 65536,
        },
    )


def tool_policy() -> ToolPolicy:
    return ToolPolicy.for_plan(planning_input())


def budget_policy() -> ResearchBudgetPolicy:
    return ResearchBudgetPolicy.for_plan(planning_input())


class RecordingRetriever:
    descriptor = ServicePortDescriptor(
        port_kind="retriever",
        owner_distribution="bijux-canon-index",
        distribution_version="0.3.10",
        implementation_module="bijux_canon_index.application.index_service",
        implementation_name="IndexService",
    )

    def __init__(self, *, mismatched: bool = False) -> None:
        self.mismatched = mismatched
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        request_hash = "0" * 64 if self.mismatched else request.request_hash()
        return RetrievalPortResult(
            request_sha256=request_hash,
            artifact_id="sha256:" + hashlib.sha256(b"retrieval").hexdigest(),
            generation_id=request.index_generation,
            records=(
                {
                    "chunk_id": "chunk-1",
                    "source_text_sha256": hashlib.sha256(b"evidence").hexdigest(),
                },
            ),
        )


class RecordingReasoner:
    descriptor = ServicePortDescriptor(
        port_kind="reasoner",
        owner_distribution="bijux-canon-reason",
        distribution_version="0.3.10",
        implementation_module="bijux_canon_reason.application.research_service",
        implementation_name="ResearchApplicationService",
    )

    def __init__(self, *, mismatched: bool = False) -> None:
        self.mismatched = mismatched
        self.requests = []

    def reason(self, request):
        self.requests.append(request)
        request_hash = "0" * 64 if self.mismatched else request.request_hash()
        return ReasoningPortResult(
            request_sha256=request_hash,
            artifact_id="sha256:" + hashlib.sha256(b"reasoning").hexdigest(),
            outcome="answered",
            text="The admitted sources report two extraction methods.",
            record={"service": "ResearchApplicationService"},
        )


class InvalidOutputRetriever(RecordingRetriever):
    def retrieve(self, request):
        self.requests.append(request)
        return {"records": []}


class InvalidOutputReasoner(RecordingReasoner):
    def reason(self, request):
        self.requests.append(request)
        return {"outcome": "answered"}


class RecordingCheckpointPort:
    def __init__(self) -> None:
        self.checkpoints: dict[str, ResearchCheckpoint] = {}
        self.persisted: list[ResearchCheckpoint] = []

    def persist(self, checkpoint: ResearchCheckpoint) -> None:
        self.checkpoints[checkpoint.artifact_id] = checkpoint
        self.persisted.append(checkpoint)

    def load(self, artifact_id: str) -> ResearchCheckpoint:
        return self.checkpoints[artifact_id]


class StaticCancellation:
    def __init__(self, signal: CancellationSignal | None = None) -> None:
        self.signal = signal or CancellationSignal.inactive()

    def current(self) -> CancellationSignal:
        return self.signal


def test_injected_services_carry_exact_requests() -> None:
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()
    services = InjectedResearchServices(retriever=retriever, reasoner=reasoner)
    plan = planning_input()

    retrieval = services.retrieve(plan)
    reasoning = services.reason(plan, retrieval)

    assert retriever.requests == [plan.retrieval_request()]
    assert reasoner.requests[0].question == plan.query
    assert reasoner.requests[0].retrieval == retrieval
    assert reasoning.outcome == "answered"
    assert services.retriever_descriptor == retriever.descriptor
    assert services.reasoner_descriptor == reasoner.descriptor


def test_injected_services_have_no_implicit_defaults() -> None:
    parameters = inspect.signature(InjectedResearchServices).parameters
    assert parameters["retriever"].default is inspect.Parameter.empty
    assert parameters["reasoner"].default is inspect.Parameter.empty
    with pytest.raises(TypeError, match="RetrieverPort"):
        InjectedResearchServices(retriever=object(), reasoner=RecordingReasoner())
    with pytest.raises(TypeError, match="ReasonerPort"):
        InjectedResearchServices(retriever=RecordingRetriever(), reasoner=object())


def test_port_descriptors_reject_wrong_owner_and_root_module() -> None:
    with pytest.raises(ValidationError, match="must be owned"):
        ServicePortDescriptor(
            port_kind="retriever",
            owner_distribution="bijux-canon-reason",
            distribution_version="0.3.10",
            implementation_module="bijux_canon_reason.application.research_service",
            implementation_name="ResearchApplicationService",
        )
    with pytest.raises(ValidationError, match="implementation_module"):
        ServicePortDescriptor(
            port_kind="retriever",
            owner_distribution="bijux-canon-index",
            distribution_version="0.3.10",
            implementation_module="bijux_canon_index",
            implementation_name="retrieve",
        )


def test_injected_services_reject_unbound_results() -> None:
    plan = planning_input()
    with pytest.raises(ValueError, match="retriever result"):
        InjectedResearchServices(
            retriever=RecordingRetriever(mismatched=True),
            reasoner=RecordingReasoner(),
        ).retrieve(plan)

    retriever = RecordingRetriever()
    retrieval = InjectedResearchServices(
        retriever=retriever,
        reasoner=RecordingReasoner(),
    ).retrieve(plan)
    with pytest.raises(ValueError, match="reasoner result"):
        InjectedResearchServices(
            retriever=retriever,
            reasoner=RecordingReasoner(mismatched=True),
        ).reason(plan, retrieval)


def test_injected_services_reject_untyped_inputs_and_outputs() -> None:
    plan = planning_input()
    with pytest.raises(TypeError, match="planning_input"):
        InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ).retrieve({})
    with pytest.raises(TypeError, match="retriever output"):
        InjectedResearchServices(
            retriever=InvalidOutputRetriever(), reasoner=RecordingReasoner()
        ).retrieve(plan)
    retrieval = InjectedResearchServices(
        retriever=RecordingRetriever(), reasoner=RecordingReasoner()
    ).retrieve(plan)
    with pytest.raises(TypeError, match="reasoner output"):
        InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=InvalidOutputReasoner()
        ).reason(plan, retrieval)


def test_research_role_machine_executes_one_operation_per_legal_edge() -> None:
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()
    services = InjectedResearchServices(retriever=retriever, reasoner=reasoner)
    checkpoints = RecordingCheckpointPort()

    result = ResearchRoleMachine(
        planning_input=planning_input(),
        services=services,
        tool_policy=tool_policy(),
        budget_policy=budget_policy(),
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    ).run()

    assert [record.operation for record in result.operations] == [
        ResearchOperation.VALIDATE_PLAN,
        ResearchOperation.RETRIEVE_EVIDENCE,
        ResearchOperation.ANALYZE_EVIDENCE,
        ResearchOperation.ASSESS_COUNTEREVIDENCE,
        ResearchOperation.RESOLVE_EVIDENCE_GAPS,
        ResearchOperation.SYNTHESIZE_ANSWER,
        ResearchOperation.VERIFY_ANSWER,
        ResearchOperation.TERMINATE_RUN,
    ]
    assert [transition.from_role for transition in result.transitions] == [
        ResearchRole.PLAN,
        ResearchRole.RETRIEVE,
        ResearchRole.ANALYZE,
        ResearchRole.SKEPTIC,
        ResearchRole.GAP_FILL,
        ResearchRole.SYNTHESIZE,
        ResearchRole.VERIFY,
        ResearchRole.TERMINATE,
    ]
    assert result.transitions[-1].to_role is ResearchRole.TERMINAL
    assert [item.sequence for item in result.operations] == list(range(8))
    assert [item.sequence for item in result.transitions] == list(range(8))
    assert [item.operation_artifact_id for item in result.transitions] == [
        item.artifact_id for item in result.operations
    ]
    assert len(retriever.requests) == 1
    assert len(reasoner.requests) == 1
    assert [decision.action for decision in result.tool_decisions] == [
        ToolPolicyAction.ALLOW,
        ToolPolicyAction.ALLOW,
    ]
    assert result.tool_policy_artifact_id == tool_policy().artifact_id
    assert result.budget_policy_artifact_id == budget_policy().artifact_id
    assert not result.exhausted_budget_dimensions
    assert all(
        decision.action is BudgetAction.CONTINUE for decision in result.budget_decisions
    )
    assert result.operations[1].payload["tool_policy_decision_artifact_id"] == (
        result.tool_decisions[0].artifact_id
    )
    assert result.operations[5].payload["tool_policy_decision_artifact_id"] == (
        result.tool_decisions[1].artifact_id
    )
    assert result.terminal_outcome == "answered"
    assert len(checkpoints.persisted) == 8
    assert result.checkpoint_artifact_id == checkpoints.persisted[-1].artifact_id
    assert len(result.causal_events) == 8
    assert result.causal_trace.event_artifact_ids == tuple(
        event.artifact_id for event in result.causal_events
    )
    assert result.causal_trace.head_artifact_id == result.causal_events[-1].artifact_id
    for sequence, event in enumerate(result.causal_events):
        assert event.sequence == sequence
        assert event.operation_artifact_id == result.operations[sequence].artifact_id
        assert event.transition_artifact_id == result.transitions[sequence].artifact_id
        assert event.state_after_artifact_id == result.transitions[sequence].artifact_id
        assert event.budget_decision_artifact_ids
        assert event.policy_artifact_ids == (
            result.tool_policy_artifact_id,
            result.budget_policy_artifact_id,
        )
        assert event.rationale
    assert result.causal_events[1].tool_decision_artifact_ids == (
        result.tool_decisions[0].artifact_id,
    )
    assert result.causal_events[5].tool_decision_artifact_ids == (
        result.tool_decisions[1].artifact_id,
    )
    assert result.retrieval is not None
    assert result.causal_events[2].observation_artifact_ids == (
        result.retrieval.artifact_id,
    )
    assert result.causal_events[2].evidence_artifact_ids == (
        "sha256:" + hashlib.sha256(b"evidence").hexdigest(),
    )


def test_research_role_machine_is_deterministic_and_terminal() -> None:
    def execute():
        return ResearchRoleMachine(
            planning_input=planning_input(),
            services=InjectedResearchServices(
                retriever=RecordingRetriever(), reasoner=RecordingReasoner()
            ),
            tool_policy=tool_policy(),
            budget_policy=budget_policy(),
            checkpoint_port=RecordingCheckpointPort(),
            cancellation_port=StaticCancellation(),
        ).run()

    first = execute()
    second = execute()
    assert first == second

    machine = ResearchRoleMachine(
        planning_input=planning_input(),
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
        tool_policy=tool_policy(),
        budget_policy=budget_policy(),
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=StaticCancellation(),
    )
    machine.run()
    assert machine.role is ResearchRole.TERMINAL
    with pytest.raises(RuntimeError, match="cannot advance"):
        machine.advance()


def test_research_role_machine_resumes_without_duplicate_tool_calls() -> None:
    plan = planning_input()
    policy = ToolPolicy.for_plan(plan)
    budget = ResearchBudgetPolicy.for_plan(plan)
    checkpoints = RecordingCheckpointPort()
    retriever = RecordingRetriever()
    machine = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=retriever, reasoner=RecordingReasoner()
        ),
        tool_policy=policy,
        budget_policy=budget,
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
        cancellation_lineage=("sha256:" + "c" * 64,),
        failure_lineage=("sha256:" + "f" * 64,),
    )
    machine.advance()
    machine.advance()
    checkpoint = machine.checkpoint
    assert checkpoint is not None
    assert len(retriever.requests) == 1

    resumed_retriever = RecordingRetriever()
    resumed_reasoner = RecordingReasoner()
    resumed = ResearchRoleMachine.resume(
        checkpoint_artifact_id=checkpoint.artifact_id,
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=resumed_retriever, reasoner=resumed_reasoner
        ),
        tool_policy=policy,
        budget_policy=budget,
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    ).run()

    assert resumed.terminal_outcome == "answered"
    assert resumed_retriever.requests == []
    assert len(resumed_reasoner.requests) == 1
    assert len(resumed.causal_events) == 8
    assert len(checkpoints.persisted) == 8
    assert checkpoints.persisted[-1].cancellation_lineage == ("sha256:" + "c" * 64,)
    assert checkpoints.persisted[-1].failure_lineage == ("sha256:" + "f" * 64,)


def test_research_role_machine_rejects_checkpoint_dependency_drift() -> None:
    plan = planning_input()
    policy = ToolPolicy.for_plan(plan)
    budget = ResearchBudgetPolicy.for_plan(plan)
    checkpoints = RecordingCheckpointPort()
    machine = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
        tool_policy=policy,
        budget_policy=budget,
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    )
    machine.advance()
    checkpoint = machine.checkpoint
    assert checkpoint is not None

    class DriftedRetriever(RecordingRetriever):
        descriptor = ServicePortDescriptor(
            port_kind="retriever",
            owner_distribution="bijux-canon-index",
            distribution_version="different",
            implementation_module="bijux_canon_index.application.index_service",
            implementation_name="IndexService",
        )

    with pytest.raises(ValueError, match="retriever_descriptor_sha256"):
        ResearchRoleMachine.resume(
            checkpoint_artifact_id=checkpoint.artifact_id,
            planning_input=plan,
            services=InjectedResearchServices(
                retriever=DriftedRetriever(), reasoner=RecordingReasoner()
            ),
            tool_policy=policy,
            budget_policy=budget,
            checkpoint_port=checkpoints,
            cancellation_port=StaticCancellation(),
        )


def test_research_checkpoint_round_trips_canonical_json() -> None:
    plan = planning_input()
    checkpoints = RecordingCheckpointPort()
    machine = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    )
    machine.advance()
    checkpoint = machine.checkpoint
    assert checkpoint is not None

    payload = checkpoint.to_payload()
    encoded = json.dumps(payload, sort_keys=True, allow_nan=False)
    restored = ResearchCheckpoint.from_payload(json.loads(encoded))

    assert restored == checkpoint
    with pytest.raises(ValueError, match="exact canonical"):
        ResearchCheckpoint.from_payload({**payload, "undeclared": True})


def test_research_role_machine_cancels_before_external_effects() -> None:
    plan = planning_input()
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()
    signal = CancellationSignal.active(
        reason="user requested stop", request_artifact_id="sha256:" + "1" * 64
    )
    result = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(retriever=retriever, reasoner=reasoner),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=StaticCancellation(signal),
    ).run()

    assert result.terminal_outcome == "cancelled:user requested stop"
    assert result.cancellation_signal == signal
    assert result.failure_records == ()
    assert retriever.requests == []
    assert reasoner.requests == []
    assert all(item.payload["status"] == "cancelled" for item in result.operations)


def test_research_role_machine_preserves_evidence_on_cooperative_cancellation() -> None:
    plan = planning_input()
    cancellation = StaticCancellation()
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()
    machine = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(retriever=retriever, reasoner=reasoner),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=cancellation,
    )
    machine.advance()
    machine.advance()
    cancellation.signal = CancellationSignal.active(
        reason="deadline reached", request_artifact_id="sha256:" + "2" * 64
    )

    result = machine.run()

    assert result.terminal_outcome == "cancelled:deadline reached"
    assert result.retrieval is not None
    assert len(retriever.requests) == 1
    assert reasoner.requests == []


@pytest.mark.parametrize(
    ("error", "kind", "retryable"),
    [
        (TimeoutError("secret timeout detail"), ResearchFailureKind.TIMEOUT, True),
        (
            ValueError("secret permanent detail"),
            ResearchFailureKind.PERMANENT_TOOL,
            False,
        ),
        (
            ConnectionError("secret connection detail"),
            ResearchFailureKind.RETRYABLE_TOOL,
            True,
        ),
    ],
)
def test_research_role_machine_classifies_failure_and_preserves_evidence(
    error: Exception,
    kind: ResearchFailureKind,
    retryable: bool,
) -> None:
    class FailingReasoner(RecordingReasoner):
        def reason(self, request):
            self.requests.append(request)
            raise error

    plan = planning_input()
    reasoner = FailingReasoner()
    checkpoints = RecordingCheckpointPort()
    machine = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=reasoner
        ),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    )
    result = machine.run()

    assert result.terminal_outcome == f"failed:{kind.value}"
    assert len(reasoner.requests) == 1
    assert len(result.failure_records) == 1
    failure = result.failure_records[0]
    assert failure.kind is kind
    assert failure.retryable is retryable
    assert failure.exception_type == type(error).__name__
    assert result.retrieval is not None
    assert failure.partial_evidence_artifact_ids[0] == result.retrieval.artifact_id
    assert "secret" not in repr(failure)

    resumed_reasoner = RecordingReasoner()
    resumed = ResearchRoleMachine.resume(
        checkpoint_artifact_id=result.checkpoint_artifact_id,
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=resumed_reasoner
        ),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=checkpoints,
        cancellation_port=StaticCancellation(),
    ).run()
    assert resumed == result
    assert resumed_reasoner.requests == []


def test_research_role_machine_rejects_skips_and_wrong_operations() -> None:
    with pytest.raises(ValueError, match="illegal research transition"):
        ResearchRoleMachine.validate_transition(
            from_role=ResearchRole.PLAN,
            to_role=ResearchRole.ANALYZE,
            operation=ResearchOperation.VALIDATE_PLAN,
        )
    with pytest.raises(ValueError, match="not owned"):
        ResearchRoleMachine.validate_transition(
            from_role=ResearchRole.PLAN,
            to_role=ResearchRole.RETRIEVE,
            operation=ResearchOperation.RETRIEVE_EVIDENCE,
        )


def test_role_machine_requires_a_plan_bound_policy() -> None:
    parameters = inspect.signature(ResearchRoleMachine).parameters
    assert parameters["tool_policy"].default is inspect.Parameter.empty
    other = planning_input().model_copy(update={"query": "A different question"})
    with pytest.raises(ValueError, match="not bound"):
        ResearchRoleMachine(
            planning_input=planning_input(),
            services=InjectedResearchServices(
                retriever=RecordingRetriever(), reasoner=RecordingReasoner()
            ),
            tool_policy=ToolPolicy.for_plan(other),
            budget_policy=ResearchBudgetPolicy.for_plan(other),
            checkpoint_port=RecordingCheckpointPort(),
            cancellation_port=StaticCancellation(),
        )


def test_role_machine_terminates_deterministically_on_global_budget() -> None:
    plan = planning_input()
    base = ResearchBudgetPolicy.for_plan(plan)
    constrained = ResearchBudgetPolicy(
        plan_sha256=base.plan_sha256,
        global_limits=BudgetDimensions(
            **{
                **base.global_limits.payload(),
                "iterations": 2,
            }
        ),
        role_limits=base.role_limits,
    )

    def execute():
        return ResearchRoleMachine(
            planning_input=plan,
            services=InjectedResearchServices(
                retriever=RecordingRetriever(), reasoner=RecordingReasoner()
            ),
            tool_policy=ToolPolicy.for_plan(plan),
            budget_policy=constrained,
            checkpoint_port=RecordingCheckpointPort(),
            cancellation_port=StaticCancellation(),
        ).run()

    first = execute()
    restarted = execute()
    assert first == restarted
    assert first.terminal_outcome == "budget_exhausted:iterations"
    assert first.exhausted_budget_dimensions == ("iterations",)
    assert first.reasoning is None
    assert first.transitions[-1].to_role is ResearchRole.TERMINAL


def test_role_machine_terminates_on_per_role_budget() -> None:
    plan = planning_input()
    base = ResearchBudgetPolicy.for_plan(plan)
    roles = dict(base.role_limits)
    roles[ResearchRole.SYNTHESIZE.value] = BudgetDimensions(
        **{
            **roles[ResearchRole.SYNTHESIZE.value].payload(),
            "provider_calls": 0,
        }
    )
    constrained = ResearchBudgetPolicy(
        plan_sha256=base.plan_sha256,
        global_limits=base.global_limits,
        role_limits=roles,
    )

    result = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=constrained,
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=StaticCancellation(),
    ).run()

    assert result.terminal_outcome == "budget_exhausted:synthesize.provider_calls"
    assert result.exhausted_budget_dimensions == ("synthesize.provider_calls",)
    assert result.reasoning is None


@pytest.mark.parametrize(
    "dimension",
    [
        "iterations",
        "retrievals",
        "candidates",
        "evidence_items",
        "tool_calls",
        "provider_calls",
        "tokens",
        "elapsed_ms",
        "retries",
        "artifact_bytes",
    ],
)
def test_budget_ledger_enforces_every_global_dimension(dimension: str) -> None:
    plan = planning_input()
    charge = BudgetDimensions(**{dimension: 1})
    ledger = ResearchBudgetLedger(
        ResearchBudgetPolicy(
            plan_sha256=plan_sha256(plan),
            global_limits=BudgetDimensions(),
            role_limits={"plan": charge},
        )
    )

    decision = ledger.charge(role="plan", label="boundary", usage=charge)

    assert decision.action is BudgetAction.TERMINATE
    assert decision.policy_artifact_id == ledger.policy.artifact_id
    assert decision.exhausted_dimensions == (dimension,)
    assert ledger.global_usage == charge


def test_policy_gateway_records_allowed_and_denied_calls() -> None:
    plan = planning_input()
    retriever = RecordingRetriever()
    gateway = PolicyEnforcedResearchServices(
        planning_input=plan,
        services=InjectedResearchServices(
            retriever=retriever, reasoner=RecordingReasoner()
        ),
        policy=ToolPolicy.for_plan(plan),
    )

    gateway.retrieve()
    with pytest.raises(ToolPolicyDenied) as error:
        gateway.retrieve()

    assert len(retriever.requests) == 1
    assert [decision.action for decision in gateway.decisions] == [
        ToolPolicyAction.ALLOW,
        ToolPolicyAction.DENY,
    ]
    assert error.value.decision.reason is ToolPolicyReason.CALL_BUDGET_EXHAUSTED
    assert error.value.decision == gateway.decisions[-1]


@pytest.mark.parametrize(
    ("changes", "reason"),
    [
        ({"tool": "fabricated.execute"}, ToolPolicyReason.TOOL_NOT_WHITELISTED),
        ({"operation": "write"}, ToolPolicyReason.OPERATION_NOT_GRANTED),
        ({"corpus_generation": "other"}, ToolPolicyReason.CORPUS_SCOPE_DENIED),
        ({"index_generation": "other"}, ToolPolicyReason.INDEX_SCOPE_DENIED),
        ({"scope": ("source:three",)}, ToolPolicyReason.LOGICAL_SCOPE_DENIED),
        ({"timeout_ms": 30001}, ToolPolicyReason.TIMEOUT_EXCEEDS_POLICY),
    ],
)
def test_tool_policy_fails_closed_for_ungranted_authority(
    changes: dict[str, object], reason: ToolPolicyReason
) -> None:
    plan = planning_input()
    fields = {
        "tool": ResearchTool.RETRIEVE.value,
        "operation": ResearchToolOperation.RETRIEVE.value,
        "plan_sha256": plan_sha256(plan),
        "request_sha256": plan.retrieval_request().request_hash(),
        "corpus_generation": plan.corpus_generation,
        "index_generation": plan.index_generation,
        "scope": plan.scope,
        "filesystem_paths": (),
        "timeout_ms": plan.budget.elapsed_ms,
        **changes,
    }
    decision = ToolPolicy.for_plan(plan).decide(
        ToolInvocation(**fields), sequence=0, prior_allowed_calls=0
    )

    assert decision.action is ToolPolicyAction.DENY
    assert decision.reason is reason


def test_tool_policy_resolves_filesystem_scope_before_authorizing(
    tmp_path,
) -> None:
    plan = planning_input()
    allowed_root = tmp_path / "allowed"
    allowed_root.mkdir(exist_ok=True)
    policy = ToolPolicy(
        plan_sha256=plan_sha256(plan),
        grants=(
            ToolGrant(
                tool=ResearchTool.FILESYSTEM_READ,
                operation=ResearchToolOperation.READ,
                corpus_generation=plan.corpus_generation,
                index_generation=plan.index_generation,
                scope=plan.scope,
                filesystem_roots=(str(allowed_root),),
                max_calls=1,
                timeout_ms=100,
            ),
        ),
    )

    def invocation(path) -> ToolInvocation:
        return ToolInvocation(
            tool=ResearchTool.FILESYSTEM_READ.value,
            operation=ResearchToolOperation.READ.value,
            plan_sha256=plan_sha256(plan),
            request_sha256="a" * 64,
            corpus_generation=plan.corpus_generation,
            index_generation=plan.index_generation,
            scope=plan.scope,
            filesystem_paths=(str(path),),
            timeout_ms=100,
        )

    allowed = policy.decide(
        invocation(allowed_root / "evidence.json"),
        sequence=0,
        prior_allowed_calls=0,
    )
    escaped = policy.decide(
        invocation(allowed_root / ".." / "outside.json"),
        sequence=1,
        prior_allowed_calls=0,
    )

    assert allowed.action is ToolPolicyAction.ALLOW
    assert escaped.action is ToolPolicyAction.DENY
    assert escaped.reason is ToolPolicyReason.FILESYSTEM_SCOPE_DENIED
