from __future__ import annotations

from dataclasses import replace
import hashlib
import inspect
import json

from pydantic import ValidationError
import pytest

from bijux_canon_agent.application import (
    AgentBehaviorDimension,
    AgentBehaviorEvaluator,
    BudgetAction,
    BudgetDimensions,
    CancellationSignal,
    InjectedResearchServices,
    PolicyEnforcedResearchServices,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
    ResearchCheckpoint,
    ResearchFailureKind,
    ResearchOperation,
    ResearchRole,
    ResearchRoleMachine,
    ToolPolicyDenied,
)
from bijux_canon_agent.contracts import (
    ReasoningPortResult,
    ResearchPlanningInput,
    ResearchTool,
    ResearchToolOperation,
    RetrievalPortResult,
    ServicePortDescriptor,
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
            "documents": 2,
            "candidates": 4,
            "evidence_items": 2,
            "tool_calls": 1,
            "provider_calls": 1,
            "tokens": 512,
            "elapsed_ms": 30000,
            "retries": 0,
            "memory_bytes": 65536,
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


class SequencedCancellation:
    def __init__(self, *signals: CancellationSignal) -> None:
        self.signals = signals
        self.calls = 0

    def current(self) -> CancellationSignal:
        signal = self.signals[min(self.calls, len(self.signals) - 1)]
        self.calls += 1
        return signal


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
    assert result.retrieval is not None
    assert result.reasoning is not None
    assert len(result.tool_descriptor_artifact_ids) == 2
    assert len(result.tool_execution_records) == 2
    assert [item.result_artifact_id for item in result.tool_execution_records] == [
        result.retrieval.artifact_id,
        result.reasoning.artifact_id,
    ]
    assert all("secret" not in repr(item) for item in result.tool_execution_records)
    assert result.operations[1].payload["tool_execution_record_artifact_id"] == (
        result.tool_execution_records[0].artifact_id
    )
    assert result.operations[5].payload["tool_execution_record_artifact_id"] == (
        result.tool_execution_records[1].artifact_id
    )
    assert result.tool_policy_artifact_id == tool_policy().artifact_id
    assert result.budget_policy_artifact_id == budget_policy().artifact_id
    assert not result.exhausted_budget_dimensions
    assert {decision.action for decision in result.budget_decisions} == {
        BudgetAction.CONTINUE,
        BudgetAction.RESERVED,
    }
    assert [
        decision.label
        for decision in result.budget_decisions
        if decision.action is BudgetAction.RESERVED
    ] == ["retrieve_evidence:reserve", "synthesize_answer:reserve"]
    assert result.operations[1].payload["tool_policy_decision_artifact_id"] == (
        result.tool_decisions[0].artifact_id
    )
    assert result.operations[5].payload["tool_policy_decision_artifact_id"] == (
        result.tool_decisions[1].artifact_id
    )
    assert result.terminal_outcome == "answered"
    assert len(checkpoints.persisted) == 8
    assert result.checkpoint_artifact_id == checkpoints.persisted[-1].artifact_id
    assert checkpoints.persisted[-1].tool_execution_records == (
        result.tool_execution_records
    )
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
    behavior = AgentBehaviorEvaluator().evaluate(result)
    assert behavior.passed
    assert all(item.passed for item in behavior.outcomes)


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


def test_agent_behavior_evaluation_retains_policy_failure() -> None:
    result = ResearchRoleMachine(
        planning_input=planning_input(),
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
        tool_policy=tool_policy(),
        budget_policy=budget_policy(),
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=StaticCancellation(),
    ).run()
    drifted = replace(result, tool_policy_artifact_id="sha256:" + "0" * 64)

    report = AgentBehaviorEvaluator().evaluate(drifted)

    assert not report.passed
    failed = tuple(item.dimension for item in report.outcomes if not item.passed)
    assert failed == (AgentBehaviorDimension.tool_policy,)


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
    assert AgentBehaviorEvaluator().evaluate(resumed).passed


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
    assert AgentBehaviorEvaluator().evaluate(result).passed


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
    assert AgentBehaviorEvaluator().evaluate(result).passed


def test_research_role_machine_records_cancellation_during_tool_execution() -> None:
    plan = planning_input()
    cancelled = CancellationSignal.active(
        reason="operator cancelled in-flight retrieval",
        request_artifact_id="sha256:" + "8" * 64,
    )
    cancellation = SequencedCancellation(
        CancellationSignal.inactive(),
        CancellationSignal.inactive(),
        CancellationSignal.inactive(),
        cancelled,
    )
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()

    result = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(retriever=retriever, reasoner=reasoner),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=ResearchBudgetPolicy.for_plan(plan),
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=cancellation,
    ).run()

    assert result.terminal_outcome == (
        "cancelled:operator cancelled in-flight retrieval"
    )
    assert result.cancellation_signal == cancelled
    assert result.failure_records == ()
    assert result.retrieval is None
    assert len(retriever.requests) == 1
    assert reasoner.requests == []
    assert result.tool_execution_records[0].status.value == "cancelled"
    assert result.tool_execution_records[0].cancellation_artifact_id == (
        cancelled.artifact_id
    )
    assert result.operations[1].payload["status"] == "cancelled"
    assert AgentBehaviorEvaluator().evaluate(result).passed


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
    assert AgentBehaviorEvaluator().evaluate(result).passed


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


def test_dynamic_document_budget_refuses_retrieval_result_before_admission() -> None:
    plan = planning_input()
    base = ResearchBudgetPolicy.for_plan(plan)
    roles = dict(base.role_limits)
    roles[ResearchRole.RETRIEVE.value] = BudgetDimensions(
        **{
            **roles[ResearchRole.RETRIEVE.value].payload(),
            "documents": 0,
        }
    )
    constrained = ResearchBudgetPolicy(
        plan_sha256=base.plan_sha256,
        global_limits=base.global_limits,
        role_limits=roles,
    )
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()

    result = ResearchRoleMachine(
        planning_input=plan,
        services=InjectedResearchServices(retriever=retriever, reasoner=reasoner),
        tool_policy=ToolPolicy.for_plan(plan),
        budget_policy=constrained,
        checkpoint_port=RecordingCheckpointPort(),
        cancellation_port=StaticCancellation(),
    ).run()

    assert result.terminal_outcome == "budget_exhausted:retrieve.documents"
    assert result.retrieval is None
    assert retriever.requests == []
    assert reasoner.requests == []
    assert result.budget_usage.retrievals == 0
    assert result.budget_usage.tool_calls == 0
    assert result.operations[1].payload["result_admitted"] is False
    assert result.operations[1].payload["exhausted_dimensions"] == [
        "retrieve.documents"
    ]


def test_memory_budget_is_peak_usage_and_refusal_does_not_consume() -> None:
    plan = planning_input()
    ledger = ResearchBudgetLedger(
        ResearchBudgetPolicy(
            plan_sha256=plan_sha256(plan),
            global_limits=BudgetDimensions(memory_bytes=100),
            role_limits={"analyze": BudgetDimensions(memory_bytes=100)},
        )
    )

    first = ledger.charge(
        role="analyze",
        label="first",
        usage=BudgetDimensions(memory_bytes=80),
    )
    second = ledger.charge(
        role="analyze",
        label="second",
        usage=BudgetDimensions(memory_bytes=50),
    )
    refused = ledger.charge(
        role="analyze",
        label="refused",
        usage=BudgetDimensions(memory_bytes=101),
    )

    assert first.action is BudgetAction.CONTINUE
    assert second.action is BudgetAction.CONTINUE
    assert second.global_usage.memory_bytes == 80
    assert refused.action is BudgetAction.TERMINATE
    assert refused.global_usage.memory_bytes == 80
    assert ledger.global_usage.memory_bytes == 80


def test_budget_reservation_is_non_consuming_and_denial_replays_exactly() -> None:
    plan = planning_input()
    policy = ResearchBudgetPolicy(
        plan_sha256=plan_sha256(plan),
        global_limits=BudgetDimensions(documents=2),
        role_limits={"retrieve": BudgetDimensions(documents=2)},
    )
    ledger = ResearchBudgetLedger(policy)

    reservation = ledger.reserve(
        role="retrieve",
        label="retrieve_evidence:reserve",
        maximum=BudgetDimensions(documents=2),
    )
    actual = ledger.charge(
        role="retrieve",
        label="retrieve_evidence:finish",
        usage=BudgetDimensions(documents=1),
    )
    denied = ledger.reserve(
        role="retrieve",
        label="retrieve_evidence:reserve",
        maximum=BudgetDimensions(documents=2),
    )

    assert reservation.action is BudgetAction.RESERVED
    assert reservation.global_usage == BudgetDimensions()
    assert actual.action is BudgetAction.CONTINUE
    assert actual.global_usage.documents == 1
    assert denied.action is BudgetAction.TERMINATE
    assert denied.global_usage.documents == 1
    restored = ResearchBudgetLedger(policy)
    restored.restore(ledger.decisions)
    assert restored.decisions == ledger.decisions
    assert restored.global_usage.documents == 1


def test_simultaneous_budget_exhaustion_reports_every_dimension() -> None:
    plan = planning_input()
    ledger = ResearchBudgetLedger(
        ResearchBudgetPolicy(
            plan_sha256=plan_sha256(plan),
            global_limits=BudgetDimensions(),
            role_limits={"retrieve": BudgetDimensions(documents=1, candidates=1)},
        )
    )

    decision = ledger.charge(
        role="retrieve",
        label="candidate batch",
        usage=BudgetDimensions(documents=1, candidates=1),
    )

    assert decision.action is BudgetAction.TERMINATE
    assert decision.exhausted_dimensions == ("documents", "candidates")
    assert ledger.global_usage == BudgetDimensions()


@pytest.mark.parametrize(
    "dimension",
    [
        "iterations",
        "retrievals",
        "documents",
        "candidates",
        "evidence_items",
        "tool_calls",
        "provider_calls",
        "tokens",
        "elapsed_ms",
        "retries",
        "memory_bytes",
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
    assert ledger.global_usage == BudgetDimensions()


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
