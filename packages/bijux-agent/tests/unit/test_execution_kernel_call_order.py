"""Execution kernel call order with a minimal agent."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import pytest

from bijux_agent.agents.base import BaseAgent
from bijux_agent.enums import AgentType, ExecutionMode
from bijux_agent.schema import AgentInput
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


class CallOrderAgent(BaseAgent):
    def __init__(self, config: dict[str, Any], logger_manager: LoggerManager) -> None:
        self.events: list[str] = []
        super().__init__(config, logger_manager)

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        self.events.append("run")
        return context

    def _revise_payload(
        self, feedback: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        self.events.append("revise_payload")
        updated = dict(context)
        updated["feedback"] = feedback
        return updated

    def error_payload(
        self,
        msg: str,
        context: dict[str, Any],
        stage: str,
        extra: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        self.events.append("fail")
        return super().error_payload(msg, context, stage, extra)


def _make_logger(tmp_path: Path) -> LoggerManager:
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))


@pytest.mark.asyncio
async def test_execution_kernel_call_order(tmp_path: Path) -> None:
    agent = CallOrderAgent({}, _make_logger(tmp_path))
    context = AgentInput(
        task_goal="order-test",
        payload={"alpha": 1},
        context_id="ctx-order",
        metadata={},
        agent_type=AgentType.PLANNER,
        execution_mode=ExecutionMode.SYNC,
    )

    await agent.run(context)
    await agent.revise(context, "tighten")
    await agent.execution_kernel.error_result("boom", context, "unit")

    assert agent.events == ["run", "revise_payload", "run", "fail"]
