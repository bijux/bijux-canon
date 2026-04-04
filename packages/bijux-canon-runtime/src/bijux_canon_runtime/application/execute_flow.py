# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# INTERNAL CORE — CHANGES REQUIRE REPLAY REVIEW

"""Module definitions for application/execute_flow.py."""

from __future__ import annotations

from dataclasses import replace
import os

from bijux_canon_runtime.application.execution_persistence import (
    ResumeState,
    load_resume_state,
    persist_run,
    resolve_read_store,
)
from bijux_canon_runtime.application.execution_policy import (
    ensure_non_determinism_policy,
    validate_non_determinism_policy,
)
from bijux_canon_runtime.application.execution_seed import derive_seed_token
from bijux_canon_runtime.application.non_determinism_lifecycle import (
    NonDeterminismLifecycle,
)
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.application.flow_execution_models import (
    ExecutionConfig,
    ExecutionStartState,
    FlowRunResult,
    PreparedFlow,
    _ExecutionStrategy,
)
from bijux_canon_runtime.core.authority import (
    authority_token,
    enforce_runtime_semantics,
)
from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.observability.capture.time import utc_now_deterministic
from bijux_canon_runtime.observability.capture.trace_recorder import TraceRecorder
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.observability.storage.execution_store_protocol import (
    ExecutionWriteStoreProtocol,
)
from bijux_canon_runtime.ontology import CausalityTag, DeterminismLevel, EventType
from bijux_canon_runtime.ontology.ids import RunID
from bijux_canon_runtime.runtime.artifact_store import (
    ArtifactStore,
    InMemoryArtifactStore,
)
from bijux_canon_runtime.runtime.budget import BudgetState
from bijux_canon_runtime.runtime.context import ExecutionContext, RunMode
from bijux_canon_runtime.runtime.execution.dry_run_executor import DryRunExecutor
from bijux_canon_runtime.runtime.execution.live_executor import LiveExecutor
from bijux_canon_runtime.runtime.execution.observer_executor import ObserverExecutor


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
        execution_config = self._effective_config()
        manifest = self._manifest
        resolved_flow = self._resolved_flow
        if (manifest is None) == (resolved_flow is None):
            raise ValueError("Provide exactly one of manifest or resolved_flow")
        if execution_config.determinism_level is None:
            raise ConfigurationError("determinism_level must be explicit")
        if resolved_flow is None:
            if manifest is None:
                raise ValueError("manifest is required when resolved_flow is absent")
            resolved_flow = ExecutionPlanner().resolve(manifest)
        if execution_config.mode == RunMode.PLAN:
            return self._prepare_plan_flow(
                resolved_flow=resolved_flow,
                execution_config=execution_config,
            )
        execution_config = self._validated_execution_config(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
        )
        strategy = self._strategy_for_mode(execution_config.mode)
        lifecycle = self._make_entropy_lifecycle(resolved_flow)
        start_state = self._load_start_state(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            lifecycle=lifecycle,
        )
        start_state = self._ensure_run_registered(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            start_state=start_state,
        )
        start_state.starting_event_index = self._record_unsafe_config_warning(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            start_state=start_state,
        )
        context = self._build_execution_context(
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
            run_id=self._require_run_id(start_state),
        )

    def _effective_config(self) -> ExecutionConfig:
        """Internal helper; not part of the public API."""
        execution_config = self._config
        strict_env = os.environ.get("BIJUX_CANON_RUNTIME_STRICT")
        if strict_env is None:
            strict_env = os.environ.get("AGENTIC_FLOWS_STRICT")
        if strict_env != "1":
            return execution_config
        if execution_config.mode in {RunMode.DRY_RUN, RunMode.UNSAFE}:
            raise ValueError("BIJUX_CANON_RUNTIME_STRICT forbids best-effort execution")
        return replace(execution_config, strict_determinism=True)

    def _prepare_plan_flow(
        self,
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
    ) -> PreparedFlow:
        """Internal helper; not part of the public API."""
        start_state = ExecutionStartState(run_id=None)
        context = self._build_execution_context(
            resolved_flow=resolved_flow,
            execution_config=execution_config,
            lifecycle=self._make_entropy_lifecycle(resolved_flow),
            start_state=start_state,
            seed=None,
            artifact_store=InMemoryArtifactStore(),
            execution_store=None,
        )
        return PreparedFlow(
            resolved_flow=resolved_flow,
            config=execution_config,
            context=context,
            strategy=LiveExecutor(),
            run_id=RunID("plan"),
        )

    def _validated_execution_config(
        self,
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
    ) -> ExecutionConfig:
        """Internal helper; not part of the public API."""
        if execution_config.execution_store is None:
            raise ValueError("execution_store is required before execution")
        if (
            execution_config.mode in {RunMode.LIVE, RunMode.OBSERVE, RunMode.UNSAFE}
            and execution_config.verification_policy is None
        ):
            raise ValueError("verification_policy is required before execution")
        if execution_config.mode not in {RunMode.LIVE, RunMode.OBSERVE, RunMode.UNSAFE}:
            return execution_config
        execution_config = ensure_non_determinism_policy(
            resolved_flow, execution_config
        )
        validate_non_determinism_policy(resolved_flow, execution_config)
        return execution_config

    def _strategy_for_mode(self, mode: RunMode) -> _ExecutionStrategy:
        """Internal helper; not part of the public API."""
        if mode == RunMode.DRY_RUN:
            return DryRunExecutor()
        if mode == RunMode.OBSERVE:
            return ObserverExecutor()
        return LiveExecutor()

    @staticmethod
    def _require_run_id(start_state: ExecutionStartState) -> RunID:
        """Internal helper; not part of the public API."""
        if start_state.run_id is None:
            raise RuntimeError("run_id must be registered before execution")
        return start_state.run_id

    @staticmethod
    def _make_entropy_lifecycle(
        resolved_flow: ExecutionPlan,
    ) -> NonDeterminismLifecycle:
        """Internal helper; not part of the public API."""
        return NonDeterminismLifecycle(
            budget=resolved_flow.manifest.entropy_budget,
            intents=resolved_flow.manifest.nondeterminism_intent,
            allowed_variance_class=resolved_flow.manifest.allowed_variance_class,
        )

    def _load_start_state(
        self,
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
        lifecycle: NonDeterminismLifecycle,
    ) -> ExecutionStartState:
        """Internal helper; not part of the public API."""
        start_state = ExecutionStartState(run_id=execution_config.resume_run_id)
        if start_state.run_id is None:
            return start_state
        read_store = resolve_read_store(execution_config)
        resume_state = load_resume_state(
            read_store,
            run_id=start_state.run_id,
            tenant_id=resolved_flow.manifest.tenant_id,
        )
        self._apply_resume_state(
            start_state=start_state,
            resume_state=resume_state,
            lifecycle=lifecycle,
        )
        return start_state

    @staticmethod
    def _apply_resume_state(
        *,
        start_state: ExecutionStartState,
        resume_state: ResumeState,
        lifecycle: NonDeterminismLifecycle,
    ) -> None:
        """Internal helper; not part of the public API."""
        start_state.resume_from_step_index = resume_state.resume_from_step_index
        start_state.starting_event_index = resume_state.starting_event_index
        start_state.starting_evidence_index = resume_state.starting_evidence_index
        start_state.starting_tool_invocation_index = (
            resume_state.starting_tool_invocation_index
        )
        start_state.starting_entropy_index = resume_state.starting_entropy_index
        start_state.initial_claim_ids = resume_state.claim_ids
        start_state.initial_artifacts = list(resume_state.artifacts)
        start_state.initial_evidence = list(resume_state.evidence)
        start_state.initial_tool_invocations = list(resume_state.tool_invocations)
        start_state.trace_recorder = TraceRecorder(resume_state.events)
        lifecycle.seed(resume_state.entropy_usage)

    @staticmethod
    def _ensure_run_registered(
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
        start_state: ExecutionStartState,
    ) -> ExecutionStartState:
        """Internal helper; not part of the public API."""
        if start_state.run_id is not None:
            return start_state
        execution_store = execution_config.execution_store
        if execution_store is None:
            raise ValueError("execution_store is required before execution")
        execution_store.register_dataset(resolved_flow.plan.dataset)
        start_state.run_id = execution_store.begin_run(
            plan=resolved_flow.plan,
            mode=execution_config.mode,
        )
        execution_store.save_steps(
            run_id=start_state.run_id,
            tenant_id=resolved_flow.plan.tenant_id,
            plan=resolved_flow.plan,
        )
        return start_state

    def _record_unsafe_config_warning(
        self,
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
        start_state: ExecutionStartState,
    ) -> int:
        """Internal helper; not part of the public API."""
        relaxed_determinism = execution_config.determinism_level in {
            DeterminismLevel.BOUNDED,
            DeterminismLevel.PROBABILISTIC,
            DeterminismLevel.UNCONSTRAINED,
        }
        permissive_verification = (
            execution_config.verification_policy is not None
            and execution_config.verification_policy.failure_mode != "halt"
        )
        if not relaxed_determinism and not permissive_verification:
            return start_state.starting_event_index
        determinism_level = execution_config.determinism_level
        if determinism_level is None:
            raise ConfigurationError("determinism_level must be explicit")
        payload: dict[str, object] = {
            "warning": "unsafe_config",
            "determinism_level": determinism_level.value,
            "verification_failure_mode": (
                execution_config.verification_policy.failure_mode
                if execution_config.verification_policy is not None
                else None
            ),
        }
        warning_event = ExecutionEvent(
            spec_version="v1",
            event_index=start_state.starting_event_index,
            step_index=0,
            event_type=EventType.SEMANTIC_VIOLATION,
            causality_tag=CausalityTag.ENVIRONMENT,
            timestamp_utc=utc_now_deterministic(start_state.starting_event_index),
            payload=payload,
            payload_hash=fingerprint_inputs(payload),
        )
        start_state.trace_recorder.record(warning_event, authority_token())
        execution_store = execution_config.execution_store
        if execution_store is not None and start_state.run_id is not None:
            execution_store.save_events(
                run_id=start_state.run_id,
                tenant_id=resolved_flow.plan.tenant_id,
                events=(warning_event,),
            )
        return start_state.starting_event_index + 1

    def _build_execution_context(
        self,
        *,
        resolved_flow: ExecutionPlan,
        execution_config: ExecutionConfig,
        lifecycle: NonDeterminismLifecycle,
        start_state: ExecutionStartState,
        seed: str | None = None,
        artifact_store: ArtifactStore | None = None,
        execution_store: ExecutionWriteStoreProtocol | None = None,
    ) -> ExecutionContext:
        """Internal helper; not part of the public API."""
        resolved_execution_store = execution_store
        if resolved_execution_store is None and execution_config.mode != RunMode.PLAN:
            resolved_execution_store = execution_config.execution_store
        resolved_seed = (
            seed if seed is not None else derive_seed_token(resolved_flow.plan)
        )
        if execution_config.mode == RunMode.PLAN:
            resolved_seed = None
        return ExecutionContext(
            authority=authority_token(),
            seed=resolved_seed,
            environment_fingerprint=resolved_flow.plan.environment_fingerprint,
            parent_flow_id=execution_config.parent_flow_id,
            child_flow_ids=execution_config.child_flow_ids or (),
            tenant_id=resolved_flow.manifest.tenant_id,
            artifact_store=artifact_store
            or execution_config.artifact_store
            or InMemoryArtifactStore(),
            trace_recorder=start_state.trace_recorder,
            mode=execution_config.mode,
            verification_policy=execution_config.verification_policy,
            observers=execution_config.observers or (),
            budget=BudgetState(execution_config.budget),
            entropy=lifecycle,
            execution_store=resolved_execution_store,
            run_id=start_state.run_id,
            resume_from_step_index=start_state.resume_from_step_index,
            starting_event_index=start_state.starting_event_index,
            starting_evidence_index=start_state.starting_evidence_index,
            starting_tool_invocation_index=start_state.starting_tool_invocation_index,
            starting_entropy_index=start_state.starting_entropy_index,
            initial_claim_ids=start_state.initial_claim_ids,
            initial_artifacts=start_state.initial_artifacts,
            initial_evidence=start_state.initial_evidence,
            initial_tool_invocations=start_state.initial_tool_invocations,
            _step_evidence={},
            _step_artifacts={},
            observed_run=execution_config.observed_run,
            strict_determinism=execution_config.strict_determinism,
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
