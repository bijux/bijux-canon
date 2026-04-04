"""Execution helpers for stage-runner agent dispatch."""

from __future__ import annotations

from typing import Any

from bijux_canon_agent.observability.logging import CustomLogger


async def execute_stage(
    stage: dict[str, Any],
    context: dict[str, Any],
    *,
    logger: CustomLogger,
) -> dict[str, Any]:
    """Execute a stage in either ensemble or single-agent mode."""
    stage_name = stage["name"]
    logger.debug(
        f"Executing stage {stage_name} with context: {context}",
        extra={"context": {"stage": stage_name}},
    )
    if "agents" in stage:
        return await _execute_ensemble_stage(stage, context, logger=logger)
    return await _execute_single_stage(stage, context, logger=logger)


async def _execute_ensemble_stage(
    stage: dict[str, Any],
    context: dict[str, Any],
    *,
    logger: CustomLogger,
) -> dict[str, Any]:
    """Execute all agents configured for an ensemble stage."""
    stage_name = stage["name"]
    results: list[dict[str, Any]] = []
    for agent_entry in stage["agents"]:
        agent = agent_entry["agent"]
        try:
            agent_result = await agent.run(context)
            results.append(agent_result)
        except Exception as exc:
            logger.error(
                f"Agent in stage '{stage_name}' failed: {exc!s}",
                extra={"context": {"stage": stage_name}},
            )
            return {"error": str(exc)}
    if results:
        return results[0]
    return {"error": "No successful agent results"}


async def _execute_single_stage(
    stage: dict[str, Any],
    context: dict[str, Any],
    *,
    logger: CustomLogger,
) -> dict[str, Any]:
    """Execute a single-agent stage."""
    stage_name = stage["name"]
    agent = stage["agent"]
    try:
        return await agent.run(context)
    except Exception as exc:
        logger.error(
            f"Agent in stage '{stage_name}' failed: {exc!s}",
            extra={"context": {"stage": stage_name}},
        )
        return {"error": str(exc)}
