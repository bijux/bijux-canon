from __future__ import annotations

import hashlib
import inspect

from pydantic import ValidationError
import pytest

from bijux_canon_agent.application import (
    InjectedResearchServices,
    ResearchOperation,
    ResearchRole,
    ResearchRoleMachine,
)
from bijux_canon_agent.contracts import (
    ReasoningPortResult,
    ResearchPlanningInput,
    RetrievalPortResult,
    ServicePortDescriptor,
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
            "iterations": 3,
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


def test_research_role_machine_executes_one_operation_per_legal_edge() -> None:
    retriever = RecordingRetriever()
    reasoner = RecordingReasoner()
    services = InjectedResearchServices(retriever=retriever, reasoner=reasoner)

    result = ResearchRoleMachine(
        planning_input=planning_input(), services=services
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
    assert result.terminal_outcome == "answered"


def test_research_role_machine_is_deterministic_and_terminal() -> None:
    def execute():
        return ResearchRoleMachine(
            planning_input=planning_input(),
            services=InjectedResearchServices(
                retriever=RecordingRetriever(), reasoner=RecordingReasoner()
            ),
        ).run()

    first = execute()
    second = execute()
    assert first == second

    machine = ResearchRoleMachine(
        planning_input=planning_input(),
        services=InjectedResearchServices(
            retriever=RecordingRetriever(), reasoner=RecordingReasoner()
        ),
    )
    machine.run()
    assert machine.role is ResearchRole.TERMINAL
    with pytest.raises(RuntimeError, match="cannot advance"):
        machine.advance()


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
