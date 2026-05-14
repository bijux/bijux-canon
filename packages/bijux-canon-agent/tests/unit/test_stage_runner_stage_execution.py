from __future__ import annotations

import pytest

from bijux_canon_agent.agents.stage_runner.stage_execution import execute_stage


class _AgentStub:
    def __init__(self, result: dict[str, object], *, fail: bool = False) -> None:
        self._result = result
        self._fail = fail

    async def run(self, _context: dict[str, object]) -> dict[str, object]:
        if self._fail:
            raise RuntimeError("boom")
        return self._result


@pytest.mark.asyncio
async def test_execute_stage_runs_single_agent(logger_manager) -> None:
    result = await execute_stage(
        {"name": "reader", "agent": _AgentStub({"text": "hello"})},
        {"file_path": "note.txt"},
        logger=logger_manager.get_logger(),
    )

    assert result == {"text": "hello"}


@pytest.mark.asyncio
async def test_execute_stage_returns_first_ensemble_result(logger_manager) -> None:
    result = await execute_stage(
        {
            "name": "ensemble",
            "agents": [
                {"agent": _AgentStub({"winner": 1}), "weight": 0.7},
                {"agent": _AgentStub({"winner": 2}), "weight": 0.3},
            ],
        },
        {"file_path": "note.txt"},
        logger=logger_manager.get_logger(),
    )

    assert result == {"winner": 1}


@pytest.mark.asyncio
async def test_execute_stage_returns_error_when_agent_fails(logger_manager) -> None:
    result = await execute_stage(
        {"name": "reader", "agent": _AgentStub({}, fail=True)},
        {"file_path": "note.txt"},
        logger=logger_manager.get_logger(),
    )

    assert result == {"error": "boom"}
