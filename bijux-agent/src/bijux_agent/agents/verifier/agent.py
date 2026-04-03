"""Verifier agent that inspects outputs for validation and veto decisions."""

from __future__ import annotations

from typing import Any

from bijux_agent.agents.base import BaseAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import DecisionOutcome, FailureMode
from bijux_agent.models.contract import AgentOutputSchema
from bijux_agent.schema import AgentOutput


class VerifierAgent(BaseAgent):
    """Re-evaluates final outputs and issues vetoes for contradictions."""

    async def _run_payload(self, context: dict[str, Any]) -> AgentOutputSchema:
        """Verify agent outputs for contradictions and emit metadata."""
        _ = context["task_goal"]
        raw_outputs = context.get("payload", {}).get("agent_outputs", [])
        if not raw_outputs:
            self.execution_kernel.fail(
                FailureMode.VALIDATION_ERROR,
                "No outputs to verify",
                None,
            )
        outputs = [AgentOutput(**entry) for entry in raw_outputs]
        contradictions = sum(self._has_contradiction(entry) for entry in outputs)
        missing_evidence = sum(
            1 for entry in outputs if not entry.metadata.get("evidence")
        )
        issues = contradictions + missing_evidence
        decision = DecisionOutcome.VETO if issues > 0 else DecisionOutcome.PASS
        output = {
            "text": "VERIFICATION_MAGNITUDE",
            "artifacts": {
                "contradictions": contradictions,
                "missing_evidence": missing_evidence,
            },
            "scores": {"issues": min(1.0, issues / 3)},
            "confidence": 1.0 if decision == DecisionOutcome.PASS else 0.25,
            "metadata": {
                "decision": decision.value,
                "contract_version": CONTRACT_VERSION,
            },
            "decision": decision.value,
        }
        validated = self.validate_output(output)
        return self._coerce_to_contract_output(validated)

    def _has_contradiction(self, entry: AgentOutput) -> int:
        """Detect contradictory wording inside a single agent output."""
        text = entry.text.lower()
        indicators = ["contradiction", "conflict", "inconsistent", "unclear"]
        return int(any(token in text for token in indicators))
