from __future__ import annotations

from typing import Any

from pydantic import ValidationError
import pytest

from bijux_agent.agents.base import BaseAgent
from bijux_agent.constants import CONTRACT_VERSION
from bijux_agent.enums import FailureMode
from bijux_agent.utilities.logger_manager import LoggerConfig, LoggerManager


class MalformedAgent(BaseAgent):
    def _initialize(self) -> None:
        pass

    def _cleanup(self) -> None:
        pass

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "text": "ok",
            "artifacts": {},
            "scores": {},
            "metadata": {"contract_version": CONTRACT_VERSION},
        }


class LowConfidenceAgent(BaseAgent):
    def _initialize(self) -> None:
        pass

    def _cleanup(self) -> None:
        pass

    async def _run_payload(self, context: dict[str, Any]) -> dict[str, Any]:
        return {
            "text": "ok",
            "artifacts": {},
            "scores": {},
            "confidence": -0.1,
            "metadata": {"contract_version": CONTRACT_VERSION},
        }


def make_logger(tmp_path):
    return LoggerManager(LoggerConfig(log_dir=tmp_path / "logs"))


def test_fail_method_raises_runtime_error(tmp_path):
    logger = make_logger(tmp_path)
    agent = MalformedAgent({}, logger)
    with pytest.raises(RuntimeError) as exc:
        agent.fail(FailureMode.TIMEOUT, "timeout")
    assert "TIMEOUT" in str(exc.value)


def test_malformed_output_triggers_validation(tmp_path):
    logger = make_logger(tmp_path)
    agent = MalformedAgent({}, logger)
    with pytest.raises(ValidationError):
        agent.validate_output(
            {
                "text": "ok",
                "artifacts": {},
                "scores": {},
                "metadata": {"contract_version": CONTRACT_VERSION},
            }
        )
