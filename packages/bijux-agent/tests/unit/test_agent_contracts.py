from __future__ import annotations

import math

from pydantic import ValidationError
import pytest

from bijux_agent.agents import JudgeAgent, PlannerAgent, VerifierAgent
from bijux_agent.agents.base import BaseAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


def make_logger(tmp_path):
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))


class StatefulAgent(BaseAgent):
    def __init__(self, config, logger):
        super().__init__(config, logger)
        self._counter = 0

    async def _run_payload(self, context):
        self._counter += 1
        return {
            "text": f"stateful-{self._counter}",
            "artifacts": {"call": self._counter},
            "scores": {"consistency": 0.5},
            "confidence": 0.5,
            "metadata": {"contract_version": CONTRACT_VERSION},
        }


@pytest.mark.parametrize(
    "agent_cls",
    [
        PlannerAgent,
        JudgeAgent,
        VerifierAgent,
    ],
)
@pytest.mark.asyncio
async def test_agents_reject_missing_required_input(tmp_path, agent_cls):
    logger = make_logger(tmp_path)
    agent = agent_cls({}, logger)
    with pytest.raises(KeyError):
        await agent.run({"payload": {}})


def test_invalid_output_raises(tmp_path):
    logger = make_logger(tmp_path)
    agent = PlannerAgent({}, logger)
    with pytest.raises(ValidationError):
        agent.validate_output(
            {
                "text": "",
                "artifacts": {},
                "scores": {},
                "confidence": 0.5,
                "metadata": {"contract_version": CONTRACT_VERSION},
            }
        )


def test_missing_confidence_is_rejected(tmp_path):
    logger = make_logger(tmp_path)
    agent = PlannerAgent({}, logger)
    with pytest.raises(ValidationError):
        agent.validate_output(
            {
                "text": "ok",
                "artifacts": {},
                "scores": {},
                "metadata": {"contract_version": CONTRACT_VERSION},
            }
        )


@pytest.mark.parametrize(
    ("confidence", "exception_type"),
    [
        (None, ValidationError),
        (math.nan, ValueError),
        (-0.1, ValueError),
        (1.5, ValueError),
    ],
)
def test_confidence_guard_rejects_invalid_values(tmp_path, confidence, exception_type):
    logger = make_logger(tmp_path)
    agent = PlannerAgent({}, logger)
    payload = {
        "text": "ok",
        "artifacts": {},
        "scores": {"quality": 0.8},
        "confidence": confidence,
        "metadata": {"contract_version": CONTRACT_VERSION},
    }
    with pytest.raises(exception_type):
        agent.validate_output(payload)


def test_missing_contract_version_rejected(tmp_path):
    logger = make_logger(tmp_path)
    agent = PlannerAgent({}, logger)
    payload = {
        "text": "ok",
        "artifacts": {},
        "scores": {"quality": 0.8},
        "confidence": 0.5,
        "metadata": {"plan_version": "unit"},
    }
    with pytest.raises(ValidationError, match="contract_version"):
        agent.validate_output(payload)


@pytest.mark.asyncio
async def test_hidden_state_is_not_allowed(tmp_path):
    logger = make_logger(tmp_path)
    agent = StatefulAgent({}, logger)
    context = {
        "task_goal": "demonstrate hidden state",
        "context_id": "hidden-state",
        "payload": {},
    }
    first_run = await agent.run(context)
    second_run = await agent.run(context)
    assert first_run != second_run


@pytest.mark.unit
@pytest.mark.asyncio
async def test_identical_input_produces_identical_plan(tmp_path):
    logger = make_logger(tmp_path)
    planner = PlannerAgent({}, logger)
    context = {
        "task_goal": "produce a plan",
        "context_id": "unit-plan",
        "payload": {"sample": True},
    }
    first_plan = await planner.run(context)
    second_plan = await planner.run(context)
    first_snapshot = first_plan.model_dump()
    second_snapshot = second_plan.model_dump()
    assert first_snapshot["artifacts"]["plan"] == second_snapshot["artifacts"]["plan"]
    assert first_plan.artifacts == second_plan.artifacts
