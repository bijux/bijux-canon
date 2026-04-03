"""Regression coverage for execution kernel delegation paths."""

from __future__ import annotations

from enum import Enum
import json
from pathlib import Path
from typing import Any

import pytest

from bijux_agent.agents.base import BaseAgent
from bijux_agent.enums import AgentType, ExecutionMode
from bijux_agent.schema import AgentInput
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


def _load_snapshot() -> dict[str, Any]:
    snapshot_path = (
        Path(__file__).resolve().parents[1]
        / "snapshots"
        / "agent_kernel_regression.json"
    )
    return json.loads(snapshot_path.read_text(encoding="utf-8"))


def _normalize_payload(value: Any) -> Any:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: _normalize_payload(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_normalize_payload(item) for item in value]
    return value


def make_logger(tmp_path: Path) -> LoggerManager:
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))


class KernelProbeAgent(BaseAgent):
    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        context = self.execution_kernel.normalize_context(context)
        return context

    def _revise_payload(
        self, feedback: dict[str, Any], context: dict[str, Any]
    ) -> dict[str, Any]:
        updated = dict(context)
        updated["feedback"] = feedback
        updated["touched"] = True
        return updated


@pytest.mark.asyncio
async def test_execution_kernel_delegation_snapshot(tmp_path: Path) -> None:
    agent = KernelProbeAgent({}, make_logger(tmp_path))
    context = AgentInput(
        task_goal="unit-test",
        payload={"alpha": 1},
        context_id="ctx-1",
        metadata={"origin": "unit"},
        agent_type=AgentType.PLANNER,
        execution_mode=ExecutionMode.SYNC,
    )

    await agent.run(context)
    revised = await agent.revise(context, "tighten")
    error_result = await agent.execution_kernel.error_result("boom", context, "unit")

    snapshot = _load_snapshot()
    actual = {
        "revised_context": _normalize_payload(revised),
        "error_result": _normalize_payload(error_result),
    }
    assert actual == snapshot
