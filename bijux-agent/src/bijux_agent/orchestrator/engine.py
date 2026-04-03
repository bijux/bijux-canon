"""Deterministic orchestration engine executing a DAG of agents."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable, Iterable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
import uuid

from bijux_agent.models.contract import (
    AgentErrorSchema,
    AgentInputSchema,
    AgentOutputSchema,
)
from bijux_agent.tracing import TraceEntry, TraceRecorder
from bijux_agent.tracing.trace import ModelMetadata

from .policy import FailurePolicy

AgentCallable = Callable[[AgentInputSchema], Awaitable[AgentOutputSchema]]


@dataclass
class AgentNode:
    """Represents a DAG node that executes an agent with retry metadata."""

    name: str
    runner: AgentCallable
    dependencies: list[str] = field(default_factory=list)
    max_retries: int = 2
    abort_on_failure: bool = True


@dataclass
class AgentExecutionState:
    """Tracks per-node outputs, errors, and retry counts for the DAG run."""

    completed: dict[str, AgentOutputSchema] = field(default_factory=dict)
    errors: dict[str, AgentErrorSchema] = field(default_factory=dict)
    attempts: dict[str, int] = field(default_factory=dict)
    aborted: bool = False

    def record_success(self, name: str, output: AgentOutputSchema) -> None:
        self.completed[name] = output
        self.attempts[name] = self.attempts.get(name, 0) + 1

    def record_error(self, name: str, error: AgentErrorSchema) -> None:
        self.errors[name] = error
        self.attempts[name] = self.attempts.get(name, 0) + 1


class Orchestrator:
    """Simple deterministic orchestrator that executes DAG nodes in order."""

    def __init__(
        self,
        nodes: Iterable[AgentNode],
        trace_path: Path | str = Path("src/bijux_agent/tracing/run_trace.json"),
        model_metadata: ModelMetadata | None = None,
        failure_policy: FailurePolicy | None = None,
    ) -> None:
        self.nodes = list(nodes)
        self.policy = failure_policy or FailurePolicy.load(Path("failure_policy.yaml"))
        self.trace_recorder = TraceRecorder(
            run_id=str(uuid.uuid4()), path=trace_path, model_metadata=model_metadata
        )

    async def run(self, initial_input: AgentInputSchema) -> AgentExecutionState:
        """Execute the DAG nodes in dependency order and record their outcomes."""
        state = AgentExecutionState()
        pending = list(self.nodes)
        context_payload = dict(initial_input.payload)

        while pending:
            executable = [
                node for node in pending if self._dependencies_met(node, state)
            ]
            if not executable:
                break
            for node in executable:
                pending.remove(node)
                context = self._prepare_context(
                    node, initial_input, state, context_payload
                )
                await self._execute(node, context, state)
                if state.aborted:
                    pending.clear()
                    break
        self.trace_recorder.finish(status="aborted" if state.aborted else "completed")
        return state

    def _dependencies_met(self, node: AgentNode, state: AgentExecutionState) -> bool:
        return all(dep in state.completed for dep in node.dependencies)

    def _prepare_context(
        self,
        node: AgentNode,
        initial_input: AgentInputSchema,
        state: AgentExecutionState,
        payload: dict[str, Any],
    ) -> AgentInputSchema:
        enriched_payload = dict(payload)
        for dep in node.dependencies:
            if dep in state.completed:
                enriched_payload[f"{dep}_output"] = state.completed[dep].model_dump()
        reduced_payload = self._apply_scope_reduction(enriched_payload)
        return AgentInputSchema(
            task_goal=initial_input.task_goal,
            payload=reduced_payload,
            context_id=".".join([initial_input.context_id, node.name]),
            metadata={
                **initial_input.metadata,
                "node": node.name,
            },
        )

    def _apply_scope_reduction(self, payload: dict[str, Any]) -> dict[str, Any]:
        reduced = dict(payload)
        for step in self.policy.scope_reduction.steps:
            if step.startswith("drop:"):
                _, key = step.split(":", 1)
                reduced.pop(key, None)
            elif step == "clear_payload":
                reduced = {}
        return reduced

    async def _execute(
        self, node: AgentNode, context: AgentInputSchema, state: AgentExecutionState
    ) -> None:
        attempt = 0
        while attempt < node.max_retries:
            attempt += 1
            start_time = datetime.now(UTC)
            try:
                output = await node.runner(context)
                state.record_success(node.name, output)
                metadata = (
                    output.metadata if isinstance(output, AgentOutputSchema) else {}
                )
                prompt_hash_value = metadata.get(
                    "prompt_hash", context.metadata.get("prompt_hash", "")
                )
                trace_entry = TraceEntry(
                    agent_id=node.name,
                    node=node.name,
                    status="success",
                    start_time=start_time,
                    end_time=datetime.now(UTC),
                    input=context.model_dump(),
                    output=output.model_dump(),
                    scores=dict(output.scores),
                    prompt_hash=prompt_hash_value,
                    model_hash=context.metadata.get("model_hash", ""),
                )
                prev_len = len(self.trace_recorder.trace.entries)
                self.trace_recorder.record_entry(trace_entry)
                if len(self.trace_recorder.trace.entries) == prev_len:
                    raise RuntimeError(f"Trace entry missing for {node.name}") from None
                return
            except Exception as exc:  # pragma: no cover
                if isinstance(exc, RuntimeError) and "Trace entry missing" in str(exc):
                    raise
                stop_reason = getattr(exc, "stop_reason", None)
                error = AgentErrorSchema(
                    code=getattr(exc, "code", "EXEC_ERROR"),
                    message=str(exc),
                    details=getattr(exc, "details", None),
                    transient=getattr(exc, "transient", attempt < node.max_retries),
                )
                state.record_error(node.name, error)
                trace_entry = TraceEntry(
                    agent_id=node.name,
                    node=node.name,
                    status="failed",
                    start_time=start_time,
                    end_time=datetime.now(UTC),
                    input=context.model_dump(),
                    output=None,
                    error=error.model_dump(),
                    prompt_hash=context.metadata.get("prompt_hash", ""),
                    model_hash=context.metadata.get("model_hash", ""),
                    scores={},
                    stop_reason=stop_reason,
                )
                prev_len = len(self.trace_recorder.trace.entries)
                self.trace_recorder.record_entry(trace_entry)
                if len(self.trace_recorder.trace.entries) == prev_len:
                    raise RuntimeError(f"Trace entry missing for {node.name}") from exc
                if error.code in self.policy.abort.critical_codes or (
                    not error.transient and node.abort_on_failure
                ):
                    state.aborted = True
                    return
                if attempt >= node.max_retries:
                    break
                await asyncio.sleep(0)
        if not state.aborted and node.abort_on_failure:
            state.aborted = True
