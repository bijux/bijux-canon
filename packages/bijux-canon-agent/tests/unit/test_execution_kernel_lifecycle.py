"""Lifecycle ordering guards for the execution kernel."""

from __future__ import annotations

from typing import Any

import pytest

from bijux_agent.agents.base import BaseAgent
from bijux_agent.agents.kernel.lifecycle import LifecyclePhase
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import FailureMode
from bijux_agent.models.contract import AgentOutputSchema


class _LifecycleProbeAgent(BaseAgent[dict[str, Any], AgentOutputSchema]):
    async def _run_payload(self, context: dict[str, Any]) -> AgentOutputSchema:
        _ = context
        return AgentOutputSchema(
            text="ok",
            artifacts={},
            scores={},
            confidence=1.0,
            metadata={"contract_version": CONTRACT_VERSION},
        )


@pytest.mark.asyncio
async def test_revise_requires_prior_run(logger_manager) -> None:
    agent = _LifecycleProbeAgent({}, logger_manager)
    context = {"task_goal": "goal", "context_id": "ctx-1", "payload": {}}
    with pytest.raises(RuntimeError, match="REVISE requires prior RUN"):
        await agent.execution_kernel.revise(
            context, feedback="fix", phase=LifecyclePhase.REVISE
        )


def test_run_cannot_follow_fail(logger_manager) -> None:
    agent = _LifecycleProbeAgent({}, logger_manager)
    with pytest.raises(RuntimeError):
        agent.execution_kernel.fail(
            FailureMode.FATAL,
            "boom",
            None,
            phase=LifecyclePhase.FAIL,
        )
    with pytest.raises(RuntimeError, match="RUN cannot occur after FAIL"):
        agent.execution_kernel.validate_context(
            {"task_goal": "goal", "context_id": "ctx-1", "payload": {}},
            phase=LifecyclePhase.RUN,
        )
