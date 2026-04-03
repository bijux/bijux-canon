"""Stage composition helpers for Pipeline."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any


class PipelineOrchestrationMixin:
    """Helper to manage custom stages and ensemble strategies."""

    logger: Any
    logger_manager: Any
    _metric_type: Any
    stage_timeout: float | int
    _stages: list[dict[str, Any]]
    _custom_ensemble_strategies: dict[
        str, Callable[[list[dict[str, Any]], list[float]], dict[str, Any]]
    ]

    def add_stage(
        self,
        name: str,
        agent: Any,
        weight: float | None = None,
        position: int | None = None,
        dependencies: list[str] | None = None,
        condition: Callable[[dict[str, Any]], bool] | None = None,
        timeout: float | None = None,
        output_key: str | None = None,
    ) -> None:
        stage = {
            "name": name,
            "dependencies": dependencies or [],
            "condition": condition or (lambda _: True),
            "timeout": timeout or self.stage_timeout,
            "output_key": output_key or name,
        }
        if weight is not None:
            stage["agents"] = [{"agent": agent, "weight": weight}]
        else:
            stage["agent"] = agent

        if position is None:
            self._stages.append(stage)
        else:
            self._stages.insert(position, stage)

        self.logger.info(
            "Added stage to Pipeline",
            extra={
                "context": {
                    "stage": name,
                    "position": position if position is not None else "end",
                    "dependencies": dependencies,
                    "timeout": timeout,
                    "output_key": output_key,
                }
            },
        )
        self.logger_manager.log_metric(
            "stages_added",
            1,
            self._metric_type.COUNTER,
            tags={"stage": name},
        )

    def register_ensemble_strategy(
        self,
        strategy_name: str,
        strategy: Callable[[list[dict[str, Any]], list[float]], dict[str, Any]],
    ) -> None:
        self._custom_ensemble_strategies[strategy_name] = strategy
        self.logger.info(
            "Registered custom ensemble strategy",
            extra={
                "context": {
                    "strategy_name": strategy_name,
                    "stage": "ensemble_strategy_registration",
                }
            },
        )
        self.logger_manager.log_metric(
            "ensemble_strategies_registered",
            1,
            self._metric_type.COUNTER,
            tags={"strategy": strategy_name},
        )
