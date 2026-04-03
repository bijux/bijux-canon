"""Judge agent enforcing normalized scoring across agent outputs."""

from __future__ import annotations

from collections import defaultdict
from statistics import mean
from typing import Any

from bijux_agent.agents.base import BaseAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome, FailureMode
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.schema import AgentOutput


class JudgeAgent(BaseAgent):
    """Aggregates multiple agent outputs into normalized decisions."""

    async def _run_payload(self, context: dict[str, Any]) -> AgentOutputSchema:
        """Aggregate scores and return a normalized judgment."""
        payload = context.get("payload", {})
        raw_outputs = payload.get("agent_outputs", [])
        if not raw_outputs:
            self.execution_kernel.fail(
                FailureMode.VALIDATION_ERROR,
                "No candidate outputs provided",
                None,
            )
        outputs = [AgentOutput(**entry) for entry in raw_outputs]
        aggregated = self._aggregate_scores(outputs)
        decision = (
            DecisionOutcome.VETO
            if aggregated.get("risk", 0.0) >= 0.5
            else DecisionOutcome.PASS
        )
        output = {
            "text": "JUDGMENT_COMPLETE",
            "artifacts": {"aggregated_scores": aggregated},
            "scores": aggregated,
            "confidence": min(1.0, mean(o.confidence for o in outputs)),
            "metadata": {
                "decision": decision.value,
                "normalized": True,
                "coverage": len(outputs),
                "contract_version": CONTRACT_VERSION,
            },
            "decision": decision.value,
        }
        validated = self.validate_output(output)
        return self._coerce_to_contract_output(validated)

    def _aggregate_scores(self, outputs: list[AgentOutput]) -> dict[str, float]:
        """Compute a weighted average of each score label."""
        weighted = defaultdict(float)
        total_weight = 0.0
        for entry in outputs:
            weight = entry.confidence
            total_weight += weight
            for label, value in entry.scores.items():
                weighted[label] += value * weight
        if total_weight == 0:
            self.execution_kernel.fail(
                FailureMode.VALIDATION_ERROR,
                "All scores lack confidence",
                None,
            )
        return {label: min(1.0, weighted[label] / total_weight) for label in weighted}
