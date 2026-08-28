"""Policy-enforced execution of injected research service ports."""

from __future__ import annotations

from collections import Counter
from typing import cast

from bijux_canon_agent.application.research_services import InjectedResearchServices
from bijux_canon_agent.contracts.execution_control import CancellationPort
from bijux_canon_agent.contracts.execution_plan import ResearchPlanningInput
from bijux_canon_agent.contracts.research_ports import (
    ReasoningPortRequest,
    ReasoningPortResult,
    RetrievalPortResult,
    ServicePortDescriptor,
)
from bijux_canon_agent.contracts.retrieval import RetrievalRequest
from bijux_canon_agent.contracts.tool_execution import (
    ResearchToolDescriptor,
    ToolExecutionRecord,
    ToolReplayPolicy,
)
from bijux_canon_agent.contracts.tool_policy import (
    ResearchTool,
    ResearchToolOperation,
    ToolInvocation,
    ToolPolicy,
    ToolPolicyAction,
    ToolPolicyDecision,
    plan_sha256,
)
from bijux_canon_agent.tooling.registry import (
    ResearchToolBinding,
    ResearchToolRegistry,
)


class ToolPolicyDenied(PermissionError):
    """A tool invocation was rejected before the port received control."""

    def __init__(self, decision: ToolPolicyDecision) -> None:
        super().__init__(
            f"tool policy denied {decision.invocation.tool}: {decision.reason.value}"
        )
        self.decision = decision


class PolicyEnforcedResearchServices:
    """Authorize, type-check, and bind every Agent service invocation."""

    def __init__(
        self,
        *,
        planning_input: ResearchPlanningInput,
        services: InjectedResearchServices,
        policy: ToolPolicy,
        cancellation_port: CancellationPort | None = None,
    ) -> None:
        if not isinstance(planning_input, ResearchPlanningInput):
            raise TypeError("planning_input must be ResearchPlanningInput")
        if not isinstance(services, InjectedResearchServices):
            raise TypeError("services must be InjectedResearchServices")
        if not isinstance(policy, ToolPolicy):
            raise TypeError("policy must be ToolPolicy")
        if policy.plan_sha256 != plan_sha256(planning_input):
            raise ValueError("tool policy is not bound to the research plan")
        self._planning_input = planning_input
        self._services = services
        self._policy = policy
        self._decisions: list[ToolPolicyDecision] = []
        self._allowed_calls: Counter[str] = Counter()
        self._registry = ResearchToolRegistry(cancellation_port=cancellation_port)
        self._register_tools()

    @property
    def policy(self) -> ToolPolicy:
        """Return the immutable policy controlling this gateway."""
        return self._policy

    @property
    def decisions(self) -> tuple[ToolPolicyDecision, ...]:
        """Return every allow or deny decision in evaluation order."""
        return tuple(self._decisions)

    @property
    def execution_records(self) -> tuple[ToolExecutionRecord, ...]:
        """Return secret-safe request/result records in call order."""
        return self._registry.records

    @property
    def tool_descriptors(self) -> tuple[ResearchToolDescriptor, ...]:
        """Return the immutable installed registry inventory."""
        return self._registry.descriptors

    @property
    def retriever_descriptor(self) -> ServicePortDescriptor:
        return self._services.retriever_descriptor

    @property
    def reasoner_descriptor(self) -> ServicePortDescriptor:
        return self._services.reasoner_descriptor

    def retrieve(self) -> RetrievalPortResult:
        """Authorize one exact retrieval request, then validate its output."""
        request = self._planning_input.retrieval_request()
        descriptor = self._descriptor(ResearchTool.RETRIEVE)
        invocation = ToolInvocation(
            tool=descriptor.tool.value,
            operation=descriptor.operation.value,
            plan_sha256=plan_sha256(self._planning_input),
            request_sha256=request.request_hash(),
            corpus_generation=request.corpus_generation,
            index_generation=request.index_generation,
            scope=request.scope,
            filesystem_paths=(),
            timeout_ms=self._planning_input.budget.elapsed_ms,
            tool_version=descriptor.version,
            input_schema_id=descriptor.input_schema_id,
            output_schema_id=descriptor.output_schema_id,
            capability=descriptor.capability,
            cost_units=descriptor.cost_units,
            idempotency_key=request.request_hash(),
        )
        decision = self._authorize(invocation)
        result = self._registry.execute(
            invocation=invocation,
            policy_decision=decision,
            request=request,
            executor=lambda _: self._services.retrieve(self._planning_input),
        )
        if not isinstance(result, RetrievalPortResult):
            raise TypeError("retriever output must be RetrievalPortResult")
        return result

    def reason(self, retrieval: RetrievalPortResult) -> ReasoningPortResult:
        """Authorize one exact reasoning request, then validate its output."""
        if not isinstance(retrieval, RetrievalPortResult):
            raise TypeError("retrieval must be RetrievalPortResult")
        request = ReasoningPortRequest(
            question=self._planning_input.query,
            retrieval=retrieval,
            constraints=self._planning_input.constraints,
            provider_profile=self._planning_input.provider_profile,
            budget=self._planning_input.budget,
        )
        descriptor = self._descriptor(ResearchTool.REASON)
        invocation = ToolInvocation(
            tool=descriptor.tool.value,
            operation=descriptor.operation.value,
            plan_sha256=plan_sha256(self._planning_input),
            request_sha256=request.request_hash(),
            corpus_generation=self._planning_input.corpus_generation,
            index_generation=self._planning_input.index_generation,
            scope=self._planning_input.scope,
            filesystem_paths=(),
            timeout_ms=self._planning_input.budget.elapsed_ms,
            tool_version=descriptor.version,
            input_schema_id=descriptor.input_schema_id,
            output_schema_id=descriptor.output_schema_id,
            capability=descriptor.capability,
            cost_units=descriptor.cost_units,
            idempotency_key=request.request_hash(),
        )
        decision = self._authorize(invocation)
        result = self._registry.execute(
            invocation=invocation,
            policy_decision=decision,
            request=request,
            executor=lambda _: self._services.reason(
                self._planning_input,
                retrieval,
            ),
        )
        if not isinstance(result, ReasoningPortResult):
            raise TypeError("reasoner output must be ReasoningPortResult")
        return result

    def authorize(self, invocation: ToolInvocation) -> ToolPolicyDecision:
        """Expose the same fail-closed gate for additional declared tools."""
        if not isinstance(invocation, ToolInvocation):
            raise TypeError("invocation must be ToolInvocation")
        return self._authorize(invocation)

    def restore(
        self,
        decisions: tuple[ToolPolicyDecision, ...],
        execution_records: tuple[ToolExecutionRecord, ...] = (),
    ) -> None:
        """Restore validated decisions without invoking any service port."""
        if self._decisions:
            raise RuntimeError("tool-policy gateway has already been used")
        for expected_sequence, decision in enumerate(decisions):
            if not isinstance(decision, ToolPolicyDecision):
                raise TypeError("restored tool decisions must be ToolPolicyDecision")
            if decision.sequence != expected_sequence:
                raise ValueError("restored tool decisions are not contiguous")
            if decision.policy_sha256 != self._policy.policy_sha256:
                raise ValueError("restored tool decision has a different policy")
            expected = self._policy.decide(
                decision.invocation,
                sequence=expected_sequence,
                prior_allowed_calls=self._allowed_calls[decision.invocation.tool],
            )
            if decision != expected:
                raise ValueError("restored tool decision failed exact validation")
            self._decisions.append(decision)
            if decision.action is ToolPolicyAction.ALLOW:
                self._allowed_calls[decision.invocation.tool] += 1
        self._registry.restore(execution_records, decisions)

    def _authorize(self, invocation: ToolInvocation) -> ToolPolicyDecision:
        decision = self._policy.decide(
            invocation,
            sequence=len(self._decisions),
            prior_allowed_calls=self._allowed_calls[invocation.tool],
        )
        self._decisions.append(decision)
        if decision.action is ToolPolicyAction.DENY:
            raise ToolPolicyDenied(decision)
        self._allowed_calls[invocation.tool] += 1
        return decision

    def _register_tools(self) -> None:
        retriever = self.retriever_descriptor
        retrieval_descriptor = ResearchToolDescriptor(
            tool=ResearchTool.RETRIEVE,
            operation=ResearchToolOperation.RETRIEVE,
            version=retriever.protocol_version,
            input_schema_id="bijux.canon.agent.retrieval-request.v1",
            output_schema_id="bijux.canon.agent.retrieval-result.v1",
            capability="corpus-retrieval",
            owner_distribution=retriever.owner_distribution,
            implementation=(
                f"{retriever.implementation_module}.{retriever.implementation_name}"
            ),
            replay_policy=ToolReplayPolicy.IDEMPOTENT_READ,
            cost_units=1,
            safe_summary_fields=(
                "artifact_id",
                "generation_id",
                "record_count",
                "status",
            ),
        )
        reasoner = self.reasoner_descriptor
        reasoning_descriptor = ResearchToolDescriptor(
            tool=ResearchTool.REASON,
            operation=ResearchToolOperation.REASON,
            version=reasoner.protocol_version,
            input_schema_id="bijux.canon.agent.reasoning-request.v1",
            output_schema_id="bijux.canon.agent.reasoning-result.v1",
            capability="evidence-reasoning",
            owner_distribution=reasoner.owner_distribution,
            implementation=(
                f"{reasoner.implementation_module}.{reasoner.implementation_name}"
            ),
            replay_policy=ToolReplayPolicy.RECORDED_ONLY,
            cost_units=1,
            safe_summary_fields=(
                "artifact_id",
                "claim_count",
                "evidence_count",
                "outcome",
                "status",
            ),
        )
        self._registry.register(
            ResearchToolBinding(
                descriptor=retrieval_descriptor,
                input_type=RetrievalRequest,
                output_type=RetrievalPortResult,
                request_identity=lambda value: cast(
                    RetrievalRequest, value
                ).request_hash(),
                result_identity=lambda value: (
                    cast(RetrievalPortResult, value).artifact_id
                ),
                safe_summary=lambda value: {
                    "artifact_id": cast(RetrievalPortResult, value).artifact_id,
                    "generation_id": cast(RetrievalPortResult, value).generation_id,
                    "record_count": len(cast(RetrievalPortResult, value).records),
                    "status": "available",
                },
            )
        )
        self._registry.register(
            ResearchToolBinding(
                descriptor=reasoning_descriptor,
                input_type=ReasoningPortRequest,
                output_type=ReasoningPortResult,
                request_identity=lambda value: cast(
                    ReasoningPortRequest, value
                ).request_hash(),
                result_identity=lambda value: (
                    cast(ReasoningPortResult, value).artifact_id
                ),
                safe_summary=lambda value: {
                    "artifact_id": cast(ReasoningPortResult, value).artifact_id,
                    "claim_count": len(
                        cast(ReasoningPortResult, value).claim_artifact_ids
                    ),
                    "evidence_count": len(
                        cast(ReasoningPortResult, value).evidence_artifact_ids
                    ),
                    "outcome": cast(ReasoningPortResult, value).outcome,
                    "status": "available",
                },
            )
        )

    def _descriptor(self, tool: ResearchTool) -> ResearchToolDescriptor:
        return next(item for item in self._registry.descriptors if item.tool is tool)


__all__ = ["PolicyEnforcedResearchServices", "ToolPolicyDenied"]
