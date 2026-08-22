from __future__ import annotations

import hashlib
from pathlib import Path

from bijux_canon_agent_trace_support import default_model_metadata
import pytest
import requests

from bijux_canon_agent.application import InjectedResearchServices
from bijux_canon_agent.application import (
    BudgetAction,
    BudgetDimensions,
    ResearchBudgetLedger,
    ResearchBudgetPolicy,
)
from bijux_canon_agent.application.workflow_graph.orchestrator import (
    WorkflowNode,
    WorkflowOrchestrator,
)
from bijux_canon_agent.application.workflow_graph.policy import (
    AbortPolicy,
    FailurePolicy,
)
from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.contracts import (
    AgentInputSchema,
    AgentOutputSchema,
    ReasoningPortResult,
    ResearchPlanningInput,
    RetrievalPortResult,
    ServicePortDescriptor,
    plan_sha256,
)
from bijux_canon_agent.llm.adapter_factory import build_adapter


def _plan(*, retrieval_mode: str, top_k: int, provider: str) -> ResearchPlanningInput:
    return ResearchPlanningInput(
        query="Which extraction methods are reported?",
        corpus_generation="corpus-generation",
        index_generation="index-generation",
        scope=("source:one",),
        top_k=top_k,
        retrieval_mode=retrieval_mode,
        constraints={"offline": provider == "Local"},
        provider_profile={
            "provider": provider,
            "model": ("local-deterministic" if provider == "Local" else "mock-model"),
            "immutable_revision": "test",
            "temperature": 0.0,
            "seed": 1,
        },
        budget={
            "iterations": 8,
            "retrievals": 1,
            "candidates": max(top_k, 4),
            "evidence_items": max(top_k, 4),
            "tool_calls": 1,
            "provider_calls": 1,
            "tokens": 100,
            "elapsed_ms": 1000,
            "retries": 0,
            "artifact_bytes": 10000,
        },
    )


class ObservingRetriever:
    descriptor = ServicePortDescriptor(
        port_kind="retriever",
        owner_distribution="bijux-canon-index",
        distribution_version="test",
        implementation_module="bijux_canon_index.application.retrieval.service",
        implementation_name="ObservingRetriever",
    )

    def __init__(self) -> None:
        self.requests = []

    def retrieve(self, request):
        self.requests.append(request)
        records = tuple(
            {
                "rank": rank,
                "source_text_sha256": hashlib.sha256(str(rank).encode()).hexdigest(),
            }
            for rank in range(request.top_k)
        )
        return RetrievalPortResult(
            request_sha256=request.request_hash(),
            artifact_id="sha256:" + hashlib.sha256(repr(records).encode()).hexdigest(),
            generation_id=request.index_generation,
            records=records,
        )


class UnusedReasoner:
    descriptor = ServicePortDescriptor(
        port_kind="reasoner",
        owner_distribution="bijux-canon-reason",
        distribution_version="test",
        implementation_module="bijux_canon_reason.application.research.service",
        implementation_name="UnusedReasoner",
    )

    def reason(self, request):
        return ReasoningPortResult(
            request_sha256=request.request_hash(),
            artifact_id="sha256:" + "a" * 64,
            outcome="answered",
            text="answer",
            record={},
        )


def test_retrieval_mode_top_k_and_provider_change_executed_requests(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def reject_network(*args, **kwargs):
        raise AssertionError("offline provider attempted network access")

    monkeypatch.setattr(requests, "post", reject_network)
    retriever = ObservingRetriever()
    services = InjectedResearchServices(retriever=retriever, reasoner=UnusedReasoner())
    lexical = _plan(retrieval_mode="lexical", top_k=1, provider="Local")
    hybrid = _plan(retrieval_mode="hybrid", top_k=3, provider="Mock")

    lexical_result = services.retrieve(lexical)
    hybrid_result = services.retrieve(hybrid)
    local_response = build_adapter({"model": lexical.provider_profile.model}).generate(
        lexical.query
    )
    mock_response = build_adapter({"model": hybrid.provider_profile.model}).generate(
        hybrid.query
    )

    assert [request.retrieval_mode for request in retriever.requests] == [
        "lexical",
        "hybrid",
    ]
    assert [request.top_k for request in retriever.requests] == [1, 3]
    assert len(lexical_result.records) == 1
    assert len(hybrid_result.records) == 3
    assert local_response.text.startswith("local::")
    assert mock_response.text == "mock response"
    assert local_response.text != mock_response.text


def test_budget_configuration_changes_execution_decisions() -> None:
    plan = _plan(retrieval_mode="lexical", top_k=1, provider="Local")
    role_limits = {"plan": BudgetDimensions(iterations=2)}
    constrained = ResearchBudgetLedger(
        ResearchBudgetPolicy(
            plan_sha256=plan_sha256(plan),
            global_limits=BudgetDimensions(iterations=1),
            role_limits=role_limits,
        )
    )
    permissive = ResearchBudgetLedger(
        ResearchBudgetPolicy(
            plan_sha256=plan_sha256(plan),
            global_limits=BudgetDimensions(iterations=2),
            role_limits=role_limits,
        )
    )
    charge = BudgetDimensions(iterations=1)

    constrained.charge(role="plan", label="first", usage=charge)
    constrained_second = constrained.charge(role="plan", label="second", usage=charge)
    permissive.charge(role="plan", label="first", usage=charge)
    permissive_second = permissive.charge(role="plan", label="second", usage=charge)

    assert constrained_second.action is BudgetAction.TERMINATE
    assert permissive_second.action is BudgetAction.CONTINUE


@pytest.mark.asyncio
async def test_role_selection_changes_nodes_that_actually_execute(
    tmp_path: Path,
) -> None:
    calls: list[str] = []

    def node(name: str) -> WorkflowNode:
        async def run(context: AgentInputSchema) -> AgentOutputSchema:
            calls.append(name)
            return AgentOutputSchema(
                text=name,
                artifacts={},
                scores={"executed": 1.0},
                confidence=1.0,
                metadata={"contract_version": CONTRACT_VERSION},
            )

        return WorkflowNode(name=name, runner=run)

    initial = AgentInputSchema(
        task_goal="observe role selection",
        payload={},
        context_id="configuration-roles",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    researcher_only = WorkflowOrchestrator(
        nodes=[node("researcher")],
        trace_path=tmp_path / "researcher.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )
    researcher_and_critic = WorkflowOrchestrator(
        nodes=[node("researcher"), node("critic")],
        trace_path=tmp_path / "critic.json",
        failure_policy=FailurePolicy(),
        model_metadata=default_model_metadata(),
    )

    first = await researcher_only.run(initial)
    first_calls = tuple(calls)
    calls.clear()
    second = await researcher_and_critic.run(initial)

    assert first_calls == ("researcher",)
    assert tuple(calls) == ("researcher", "critic")
    assert tuple(first.completed) == ("researcher",)
    assert tuple(second.completed) == ("researcher", "critic")


@pytest.mark.asyncio
async def test_failure_policy_changes_retry_execution(tmp_path: Path) -> None:
    class ConfiguredFailure(RuntimeError):
        code = "CONFIGURED"

    attempts = {"critical": 0, "retry": 0}

    def failing_node(label: str) -> WorkflowNode:
        async def run(context: AgentInputSchema) -> AgentOutputSchema:
            attempts[label] += 1
            raise ConfiguredFailure("expected")

        return WorkflowNode(name=label, runner=run, max_retries=2)

    initial = AgentInputSchema(
        task_goal="observe failure policy",
        payload={},
        context_id="configuration-failure",
        metadata={"contract_version": CONTRACT_VERSION},
    )
    critical = WorkflowOrchestrator(
        nodes=[failing_node("critical")],
        trace_path=tmp_path / "critical.json",
        failure_policy=FailurePolicy(abort=AbortPolicy(critical_codes=["CONFIGURED"])),
        model_metadata=default_model_metadata(),
    )
    retry = WorkflowOrchestrator(
        nodes=[failing_node("retry")],
        trace_path=tmp_path / "retry.json",
        failure_policy=FailurePolicy(abort=AbortPolicy(critical_codes=[])),
        model_metadata=default_model_metadata(),
    )

    await critical.run(initial)
    await retry.run(initial)

    assert attempts == {"critical": 1, "retry": 2}
