from __future__ import annotations

import math

from pydantic import ValidationError
import pytest

from bijux_canon_agent.agents import JudgeAgent, PlannerAgent, VerifierAgent
from bijux_canon_agent.agents.base import BaseAgent
from bijux_canon_agent.constants import CONTRACT_VERSION
from bijux_canon_agent.observability.logging import LoggerConfig, LoggerManager


def make_logger(tmp_path):
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))


def planning_input(query: str) -> dict[str, object]:
    return {
        "query": query,
        "corpus_generation": "corpus:ancient-dna:2026-08-21",
        "index_generation": "index:ancient-dna:lexical:2026-08-21",
        "scope": ["source:d01_fastq", "source:d02_alignment"],
        "top_k": 4,
        "retrieval_mode": "lexical",
        "constraints": {"require_exact_citations": True, "language": "en"},
        "provider_profile": {
            "provider": "bijux",
            "model": "baseline-extractive",
            "immutable_revision": "0.3.10",
            "temperature": 0.0,
            "seed": 17,
        },
        "budget": {
            "iterations": 3,
            "retrievals": 2,
            "documents": 4,
            "candidates": 8,
            "evidence_items": 4,
            "tool_calls": 3,
            "provider_calls": 2,
            "tokens": 512,
            "elapsed_ms": 30000,
            "retries": 1,
            "memory_bytes": 65536,
            "artifact_bytes": 65536,
        },
    }


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
        "payload": {"planning_input": planning_input("produce a plan")},
    }
    first_plan = await planner.run(context)
    second_plan = await planner.run(context)
    first_snapshot = first_plan.model_dump()
    second_snapshot = second_plan.model_dump()
    assert first_snapshot["artifacts"]["plan"] == second_snapshot["artifacts"]["plan"]
    assert first_plan.artifacts == second_plan.artifacts


@pytest.mark.asyncio
async def test_planner_carries_every_planning_input(tmp_path):
    logger = make_logger(tmp_path)
    planner = PlannerAgent({}, logger)
    expected = planning_input("Compare ancient-DNA alignment methods")

    result = await planner.run(
        {
            "task_goal": expected["query"],
            "context_id": "complete-plan",
            "payload": {"planning_input": expected},
        }
    )

    plan = result.artifacts["plan"]
    assert plan["planning_input"] == expected
    retrieval = plan["retrieval_steps"][0]
    for field in (
        "query",
        "corpus_generation",
        "index_generation",
        "scope",
        "top_k",
        "retrieval_mode",
        "constraints",
    ):
        assert retrieval[field] == expected[field]
    assert result.metadata["plan_version"] == "2.0"
    assert len(result.metadata["planning_input_sha256"]) == 64


@pytest.mark.asyncio
async def test_planner_rejects_missing_or_divergent_planning_input(tmp_path):
    logger = make_logger(tmp_path)
    planner = PlannerAgent({}, logger)
    with pytest.raises(ValidationError, match="corpus_generation"):
        await planner.run(
            {"task_goal": "research", "context_id": "missing-plan", "payload": {}}
        )

    divergent = planning_input("different query")
    with pytest.raises(ValueError, match="must equal"):
        await planner.run(
            {
                "task_goal": "requested query",
                "context_id": "divergent-plan",
                "payload": {"planning_input": divergent},
            }
        )


@pytest.mark.asyncio
async def test_planner_rejects_retrieval_beyond_budget(tmp_path):
    logger = make_logger(tmp_path)
    planner = PlannerAgent({}, logger)
    invalid = planning_input("bounded query")
    invalid["top_k"] = 9
    with pytest.raises(ValidationError, match="candidate budget"):
        await planner.run(
            {
                "task_goal": "bounded query",
                "context_id": "over-budget-plan",
                "payload": {"planning_input": invalid},
            }
        )
