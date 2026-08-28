"""Planner agent producing deterministic execution plans."""

from __future__ import annotations

from collections.abc import Mapping
import hashlib
import json
from typing import Any

from bijux_canon_agent.agents.base import BaseAgent
from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.contracts import ExecutionPlan, ResearchPlanningInput
from bijux_canon_agent.contracts.agent_contract import AgentOutputSchema
from bijux_canon_agent.enums import AgentType, DecisionOutcome


class PlannerAgent(BaseAgent[dict[str, Any], AgentOutputSchema]):
    """Creates execution DAGs, sequences, and required retrieval actions."""

    async def _run_payload(self, context: dict[str, Any]) -> AgentOutputSchema:
        """Build a deterministic plan and serialize it."""
        plan = self._build_plan(context)
        planning_input = plan.planning_input.model_dump(mode="json")
        planning_input_sha256 = hashlib.sha256(
            json.dumps(
                planning_input,
                sort_keys=True,
                separators=(",", ":"),
                ensure_ascii=False,
                allow_nan=False,
            ).encode("utf-8")
        ).hexdigest()
        output = {
            "text": "PLAN_READY",
            "artifacts": {"plan": plan.model_dump(mode="json")},
            "scores": {"planning_confidence": 0.95},
            "confidence": 0.92,
            "metadata": {
                "plan_version": "2.0",
                "planning_input_sha256": planning_input_sha256,
                "contract_version": CONTRACT_VERSION,
            },
            "decision": DecisionOutcome.PASS.value,
        }
        validated = self.validate_output(output)
        return self._coerce_to_contract_output(validated)

    def _build_plan(self, context: dict[str, Any]) -> ExecutionPlan:
        """Construct a plan from explicit user, retrieval, provider, and limits."""
        raw_planning_input = context.get("planning_input")
        if raw_planning_input is None:
            raw_planning_input = {
                "query": context["task_goal"],
                **{
                    key: context[key]
                    for key in (
                        "corpus_generation",
                        "index_generation",
                        "scope",
                        "top_k",
                        "retrieval_mode",
                        "constraints",
                        "provider_profile",
                        "budget",
                    )
                    if key in context
                },
            }
        if not isinstance(raw_planning_input, Mapping):
            raise TypeError("planning_input must be a mapping")
        planning_input = ResearchPlanningInput(**dict(raw_planning_input))
        if planning_input.query != context["task_goal"]:
            raise ValueError("planning input query must equal the requested task goal")
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
        retrieval = planning_input.retrieval_request()
        return ExecutionPlan(
            planning_input=planning_input,
            dag=dag,
            sequence=sequence,
            retrieval_steps=[retrieval],
        )
