# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# INTERNAL CORE — CHANGES REQUIRE REPLAY REVIEW

"""Module definitions for application/execute_flow.py."""

from __future__ import annotations

from bijux_canon_runtime.application.execution_persistence import persist_run
from bijux_canon_runtime.application.flow_execution_models import (
    ExecutionConfig,
    FlowRunResult,
    PreparedFlow,
)
from bijux_canon_runtime.application.flow_preparation_support import (
    build_execution_context,
    effective_execution_config,
    ensure_run_registered,
    load_start_state,
    make_entropy_lifecycle,
    prepare_plan_flow,
    record_unsafe_config_warning,
    require_run_id,
    strategy_for_mode,
    validated_execution_config,
)
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.core.authority import (
    enforce_runtime_semantics,
)
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.flows.manifest import FlowManifest


class FlowPreparation:
    """Prepare flow execution and build execution context."""

    def __init__(
        self,
        *,
        manifest: FlowManifest | None,
        resolved_flow: ExecutionPlan | None,
        config: ExecutionConfig,
    ) -> None:
        self._manifest = manifest
        self._resolved_flow = resolved_flow
        self._config = config

    def run(self) -> PreparedFlow:
        """Execute preparation and enforce its contract."""
        execution_config = effective_execution_config(self._config)
        manifest = self._manifest
        resolved_flow = self._resolved_flow
        if (manifest is None) == (resolved_flow is None):
            raise ValueError("Provide exactly one of manifest or resolved_flow")
        if execution_config.determinism_level is None:
            raise ValueError("determinism_level must be explicit")
        if resolved_flow is None:
            if manifest is None:
                raise ValueError("manifest is required when resolved_flow is absent")
            resolved_flow = ExecutionPlanner().resolve(manifest)
        if execution_config.mode == RunMode.PLAN:
            return prepare_plan_flow(
                resolved_flow=resolved_flow,
                execution_config=execution_config,
            )
        execution_config = validated_execution_config(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
        )
        strategy = strategy_for_mode(execution_config.mode)
        lifecycle = make_entropy_lifecycle(resolved_flow)
        start_state = load_start_state(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            lifecycle=lifecycle,
        )
        start_state = ensure_run_registered(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            start_state=start_state,
        )
        start_state.starting_event_index = record_unsafe_config_warning(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            start_state=start_state,
        )
        context = build_execution_context(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            lifecycle=lifecycle,
            start_state=start_state,
        )
        return PreparedFlow(
            resolved_flow=resolved_flow,
            config=execution_config,
            context=context,
            strategy=strategy,
            run_id=require_run_id(start_state),
        )


class FlowExecution:
    """Execute a prepared flow."""

    def __init__(self, *, prepared: PreparedFlow) -> None:
        self._prepared = prepared

    def run(self) -> FlowRunResult:
        """Execute execution and enforce its contract."""
        outcome = self._prepared.strategy.execute(
            self._prepared.resolved_flow, self._prepared.context
        )
        return FlowRunResult(
            resolved_flow=self._prepared.resolved_flow,
            trace=outcome.trace,
            artifacts=outcome.artifacts,
            evidence=outcome.evidence,
            reasoning_bundles=outcome.reasoning_bundles,
            verification_results=outcome.verification_results,
            verification_arbitrations=outcome.verification_arbitrations,
            run_id=self._prepared.run_id,
        )


class FlowFinalization:
    """Finalize flow execution and persistence."""

    def __init__(self, *, prepared: PreparedFlow) -> None:
        self._prepared = prepared

    def run(self, result: FlowRunResult) -> FlowRunResult:
        """Execute finalization and enforce its contract."""
        enforce_runtime_semantics(result, mode=self._prepared.config.mode.value)
        if self._prepared.config.mode == RunMode.PLAN:
            return result
        return persist_run(result, self._prepared.config)


def execute_flow(
    manifest: FlowManifest | None = None,
    *,
    resolved_flow: ExecutionPlan | None = None,
    config: ExecutionConfig | None = None,
) -> FlowRunResult:
    """Execution lifecycle contract.

    - Phases (order): planning -> execution -> finalization.
    - Restartable: planning, execution (resume from last checkpoint).
    - Irreversible: dataset registration, run begin, persisted writes, finalization.
    """
    execution_config = config or ExecutionConfig(
        mode=RunMode.LIVE,
        determinism_level=None,
    )
    preparation = FlowPreparation(
        manifest=manifest, resolved_flow=resolved_flow, config=execution_config
    )
    prepared = preparation.run()
    if prepared.config.mode == RunMode.PLAN:
        return FlowRunResult(
            resolved_flow=prepared.resolved_flow,
            trace=None,
            artifacts=[],
            evidence=[],
            reasoning_bundles=[],
            verification_results=[],
            verification_arbitrations=[],
            run_id=None,
        )
    execution = FlowExecution(prepared=prepared)
    result = execution.run()
    finalization = FlowFinalization(prepared=prepared)
    return finalization.run(result)


__all__ = ["ExecutionConfig", "FlowRunResult", "RunMode", "execute_flow"]
