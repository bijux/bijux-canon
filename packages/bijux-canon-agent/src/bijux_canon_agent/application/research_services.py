"""Fail-closed composition of Agent-owned research service ports."""

from __future__ import annotations

from bijux_canon_agent.contracts.execution_plan import ResearchPlanningInput
from bijux_canon_agent.contracts.research_ports import (
    ReasonerPort,
    ReasoningPortRequest,
    ReasoningPortResult,
    RetrievalPortResult,
    RetrieverPort,
    ServicePortDescriptor,
)


class InjectedResearchServices:
    """Bind explicit retrieval and reasoning implementations without discovery."""

    def __init__(self, *, retriever: RetrieverPort, reasoner: ReasonerPort) -> None:
        if not isinstance(retriever, RetrieverPort):
            raise TypeError("retriever must implement RetrieverPort")
        if not isinstance(reasoner, ReasonerPort):
            raise TypeError("reasoner must implement ReasonerPort")
        if retriever.descriptor.port_kind != "retriever":
            raise ValueError("retriever descriptor has the wrong port kind")
        if reasoner.descriptor.port_kind != "reasoner":
            raise ValueError("reasoner descriptor has the wrong port kind")
        self._retriever = retriever
        self._reasoner = reasoner

    @property
    def retriever_descriptor(self) -> ServicePortDescriptor:
        """Return the exact installed retrieval adapter identity."""
        return self._retriever.descriptor

    @property
    def reasoner_descriptor(self) -> ServicePortDescriptor:
        """Return the exact installed reasoning adapter identity."""
        return self._reasoner.descriptor

    def retrieve(self, planning_input: ResearchPlanningInput) -> RetrievalPortResult:
        """Execute the injected retriever and bind its result to the request."""
        request = planning_input.retrieval_request()
        result = self._retriever.retrieve(request)
        if result.request_sha256 != request.request_hash():
            raise ValueError("retriever result does not match its request")
        if result.generation_id != planning_input.index_generation:
            raise ValueError("retriever returned an undeclared index generation")
        if len(result.records) > planning_input.top_k:
            raise ValueError("retriever returned more records than requested")
        return result

    def reason(
        self,
        planning_input: ResearchPlanningInput,
        retrieval: RetrievalPortResult,
    ) -> ReasoningPortResult:
        """Execute the injected reasoner and bind its result to the request."""
        request = ReasoningPortRequest(
            question=planning_input.query,
            retrieval=retrieval,
            constraints=planning_input.constraints,
            provider_profile=planning_input.provider_profile,
            budget=planning_input.budget,
        )
        result = self._reasoner.reason(request)
        if result.request_sha256 != request.request_hash():
            raise ValueError("reasoner result does not match its request")
        return result


__all__ = ["InjectedResearchServices"]
