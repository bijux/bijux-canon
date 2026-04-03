"""Planner agent producing deterministic execution plans."""

from __future__ import annotations

from typing import Any

from bijux_agent.agents.base import BaseAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import AgentType, DecisionOutcome
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.retrieval.interfaces import RetrievalRequest
from bijux_agent.schema import ExecutionPlan


class PlannerAgent(BaseAgent):
    """Creates execution DAGs, sequences, and required retrieval actions."""

    async def _run_payload(self, context: dict[str, Any]) -> AgentOutputSchema:
        """Build a deterministic plan and serialize it."""
        plan = self._build_plan()
        output = {
            "text": "PLAN_READY",
            "artifacts": {"plan": plan.model_dump()},
            "scores": {"planning_confidence": 0.95},
            "confidence": 0.92,
            "metadata": {
                "plan_version": "1.0",
                "contract_version": CONTRACT_VERSION,
            },
            "decision": DecisionOutcome.PASS.value,
        }
        validated = self.validate_output(output)
        return self._coerce_to_contract_output(validated)

    def _build_plan(self) -> ExecutionPlan:
        """Construct the static DAG, sequence, and retrieval dependencies."""
        dag = [
            (AgentType.READER.value, AgentType.SUMMARIZER.value),
            (AgentType.SUMMARIZER.value, AgentType.CRITIQUE.value),
            (AgentType.CRITIQUE.value, AgentType.VERIFIER.value),
        ]
        sequence = [
            AgentType.READER,
            AgentType.SUMMARIZER,
            AgentType.CRITIQUE,
            AgentType.VERIFIER,
        ]
        retrieval = RetrievalRequest(
            query="Extract core requirements",
            top_k=3,
            filters=["regulation", "summaries"],
        )
        return ExecutionPlan(dag=dag, sequence=sequence, retrieval_steps=[retrieval])
