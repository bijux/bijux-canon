# INTERNAL — NOT A PUBLIC EXTENSION POINT
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# INTERNAL CORE — CHANGES REQUIRE REPLAY REVIEW

"""Module definitions for application/execute_flow.py."""

from __future__ import annotations

from dataclasses import dataclass, replace
import os

from bijux_canon_runtime.core.authority import authority_token, enforce_runtime_semantics
from bijux_canon_runtime.core.errors import ConfigurationError
from bijux_canon_runtime.runtime.artifact_store import ArtifactStore, InMemoryArtifactStore
from bijux_canon_runtime.runtime.budget import BudgetState, ExecutionBudget
from bijux_canon_runtime.runtime.context import ExecutionContext, RunMode
from bijux_canon_runtime.runtime.execution.dry_run_executor import DryRunExecutor
from bijux_canon_runtime.runtime.execution.live_executor import LiveExecutor
from bijux_canon_runtime.runtime.execution.observer_executor import ObserverExecutor
from bijux_canon_runtime.observability.capture.hooks import RuntimeObserver
from bijux_canon_runtime.observability.capture.observed_run import ObservedRun
from bijux_canon_runtime.observability.capture.time import utc_now_deterministic
from bijux_canon_runtime.observability.capture.trace_recorder import TraceRecorder
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionReadStore,
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.observability.storage.execution_store_protocol import (
    ExecutionReadStoreProtocol,
    ExecutionWriteStoreProtocol,
)
from bijux_canon_runtime.application.non_determinism_lifecycle import (
    NonDeterminismLifecycle,
)
from bijux_canon_runtime.application.execution_policy import (
    ensure_non_determinism_policy,
    validate_non_determinism_policy,
)
from bijux_canon_runtime.application.execution_persistence import (
    ResumeState,
    load_resume_state,
    persist_run,
    resolve_read_store,
)
from bijux_canon_runtime.application.execution_seed import derive_seed_token
from bijux_canon_runtime.application.planner import ExecutionPlanner
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.execution.execution_steps import ExecutionSteps
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.flows.manifest import FlowManifest
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.policy.non_determinism_policy import NonDeterminismPolicy
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import VerificationResult
from bijux_canon_runtime.ontology import CausalityTag, DeterminismLevel, EventType
from bijux_canon_runtime.ontology.ids import FlowID, RunID


@dataclass(frozen=True)
class FlowRunResult:
    """Execution result record; misuse breaks run auditability."""

    resolved_flow: ExecutionPlan
    trace: ExecutionTrace | None
    artifacts: list[Artifact]
    evidence: list[RetrievedEvidence]
    reasoning_bundles: list[ReasoningBundle]
    verification_results: list[VerificationResult]
    verification_arbitrations: list[VerificationArbitration]
    run_id: RunID | None = None


@dataclass(frozen=True)
class ExecutionConfig:
    """Execution config; misuse breaks execution invariants."""

    mode: RunMode
    determinism_level: DeterminismLevel | None
    verification_policy: VerificationPolicy | None = None
    non_determinism_policy: NonDeterminismPolicy | None = None
    artifact_store: ArtifactStore | None = None
    execution_store: ExecutionWriteStoreProtocol | None = None
    execution_read_store: ExecutionReadStoreProtocol | None = None
    budget: ExecutionBudget | None = None
    observed_run: ObservedRun | None = None
    parent_flow_id: FlowID | None = None
    child_flow_ids: tuple[FlowID, ...] | None = None
    observers: tuple[RuntimeObserver, ...] | None = None
    resume_run_id: RunID | None = None
    strict_determinism: bool = False

    @classmethod
    def from_command(cls, command: str) -> ExecutionConfig:
        """Execute from_command and enforce its contract."""
        if command == "plan":
            return cls(mode=RunMode.PLAN, determinism_level=None)
        if command == "dry-run":
            return cls(mode=RunMode.DRY_RUN, determinism_level=None)
        if command == "run":
            return cls(mode=RunMode.LIVE, determinism_level=None)
        if command == "observe":
            return cls(mode=RunMode.OBSERVE, determinism_level=None)
        if command == "unsafe-run":
            return cls(mode=RunMode.UNSAFE, determinism_level=None)
        raise ValueError(f"Unsupported command: {command}")


@dataclass(frozen=True)
class PreparedFlow:
    """Prepared flow; misuse breaks execution invariants."""

    resolved_flow: ExecutionPlan
    config: ExecutionConfig
    context: ExecutionContext
    strategy: object
    run_id: RunID


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
        execution_config = self._config
        manifest = self._manifest
        resolved_flow = self._resolved_flow
        strict_env = os.environ.get("BIJUX_CANON_RUNTIME_STRICT")
        if strict_env is None:
            strict_env = os.environ.get("AGENTIC_FLOWS_STRICT")
        if strict_env == "1":
            if execution_config.mode in {RunMode.DRY_RUN, RunMode.UNSAFE}:
                raise ValueError(
                    "BIJUX_CANON_RUNTIME_STRICT forbids best-effort execution"
                )
            execution_config = replace(execution_config, strict_determinism=True)
        if (manifest is None) == (resolved_flow is None):
            raise ValueError("Provide exactly one of manifest or resolved_flow")
        if execution_config.determinism_level is None:
            raise ConfigurationError("determinism_level must be explicit")
        if resolved_flow is None:
            resolved_flow = ExecutionPlanner().resolve(manifest)

        if execution_config.mode == RunMode.PLAN:
            context = ExecutionContext(
                authority=authority_token(),
                seed=None,
                environment_fingerprint=resolved_flow.plan.environment_fingerprint,
                parent_flow_id=execution_config.parent_flow_id,
                child_flow_ids=execution_config.child_flow_ids or (),
                tenant_id=resolved_flow.manifest.tenant_id,
                artifact_store=InMemoryArtifactStore(),
                trace_recorder=TraceRecorder(),
                mode=execution_config.mode,
                verification_policy=execution_config.verification_policy,
                observers=execution_config.observers or (),
                budget=BudgetState(execution_config.budget),
                entropy=NonDeterminismLifecycle(
                    budget=resolved_flow.manifest.entropy_budget,
                    intents=resolved_flow.manifest.nondeterminism_intent,
                    allowed_variance_class=resolved_flow.manifest.allowed_variance_class,
                ),
                execution_store=None,
                run_id=None,
                resume_from_step_index=-1,
                starting_event_index=0,
                starting_evidence_index=0,
                starting_tool_invocation_index=0,
                starting_entropy_index=0,
                initial_claim_ids=(),
                initial_artifacts=[],
                initial_evidence=[],
                initial_tool_invocations=[],
                _step_evidence={},
                _step_artifacts={},
                observed_run=execution_config.observed_run,
                strict_determinism=execution_config.strict_determinism,
            )
            return PreparedFlow(
                resolved_flow=resolved_flow,
                config=execution_config,
                context=context,
                strategy=LiveExecutor(),
                run_id=RunID("plan"),
            )
        if execution_config.execution_store is None:
            raise ValueError("execution_store is required before execution")

        if (
            execution_config.mode in {RunMode.LIVE, RunMode.OBSERVE, RunMode.UNSAFE}
            and execution_config.verification_policy is None
        ):
            raise ValueError("verification_policy is required before execution")
        if execution_config.mode in {RunMode.LIVE, RunMode.OBSERVE, RunMode.UNSAFE}:
            execution_config = ensure_non_determinism_policy(
                resolved_flow, execution_config
            )
            validate_non_determinism_policy(resolved_flow, execution_config)

        strategy = LiveExecutor()
        if execution_config.mode == RunMode.DRY_RUN:
            strategy = DryRunExecutor()
        if execution_config.mode == RunMode.OBSERVE:
            strategy = ObserverExecutor()

        store = execution_config.artifact_store or InMemoryArtifactStore()
        run_id = execution_config.resume_run_id
        resume_from_step_index = -1
        starting_event_index = 0
        starting_evidence_index = 0
        starting_tool_invocation_index = 0
        starting_entropy_index = 0
        initial_claim_ids = ()
        initial_artifacts: list[Artifact] = []
        initial_evidence: list[RetrievedEvidence] = []
        initial_tool_invocations: list[ToolInvocation] = []
        trace_recorder = TraceRecorder()
        lifecycle = NonDeterminismLifecycle(
            budget=resolved_flow.manifest.entropy_budget,
            intents=resolved_flow.manifest.nondeterminism_intent,
            allowed_variance_class=resolved_flow.manifest.allowed_variance_class,
        )
        if run_id is not None:
            read_store = resolve_read_store(execution_config)
            resume_state = load_resume_state(
                read_store, run_id=run_id, tenant_id=resolved_flow.manifest.tenant_id
            )
            resume_from_step_index = resume_state.resume_from_step_index
            starting_event_index = resume_state.starting_event_index
            starting_evidence_index = resume_state.starting_evidence_index
            starting_tool_invocation_index = resume_state.starting_tool_invocation_index
            starting_entropy_index = resume_state.starting_entropy_index
            initial_claim_ids = resume_state.claim_ids
            initial_artifacts = list(resume_state.artifacts)
            initial_evidence = list(resume_state.evidence)
            initial_tool_invocations = list(resume_state.tool_invocations)
            trace_recorder = TraceRecorder(resume_state.events)
            lifecycle.seed(resume_state.entropy_usage)
        if run_id is None:
            execution_config.execution_store.register_dataset(
                resolved_flow.plan.dataset
            )
            run_id = execution_config.execution_store.begin_run(
                plan=resolved_flow.plan, mode=execution_config.mode
            )
            execution_config.execution_store.save_steps(
                run_id=run_id,
                tenant_id=resolved_flow.plan.tenant_id,
                plan=resolved_flow.plan,
            )
        relaxed_determinism = execution_config.determinism_level in {
            DeterminismLevel.BOUNDED,
            DeterminismLevel.PROBABILISTIC,
            DeterminismLevel.UNCONSTRAINED,
        }
        permissive_verification = (
            execution_config.verification_policy is not None
            and execution_config.verification_policy.failure_mode != "halt"
        )
        if relaxed_determinism or permissive_verification:
            payload = {
                "warning": "unsafe_config",
                "determinism_level": execution_config.determinism_level.value,
                "verification_failure_mode": (
                    execution_config.verification_policy.failure_mode
                    if execution_config.verification_policy is not None
                    else None
                ),
            }
            warning_event = ExecutionEvent(
                spec_version="v1",
                event_index=starting_event_index,
                step_index=0,
                event_type=EventType.SEMANTIC_VIOLATION,
                causality_tag=CausalityTag.ENVIRONMENT,
                timestamp_utc=utc_now_deterministic(starting_event_index),
                payload=payload,
                payload_hash=fingerprint_inputs(payload),
            )
            trace_recorder.record(warning_event, authority_token())
            if execution_config.execution_store is not None and run_id is not None:
                execution_config.execution_store.save_events(
                    run_id=run_id,
                    tenant_id=resolved_flow.plan.tenant_id,
                    events=(warning_event,),
                )
            starting_event_index += 1
        seed = derive_seed_token(resolved_flow.plan)
        context = ExecutionContext(
            authority=authority_token(),
            seed=seed,
            environment_fingerprint=resolved_flow.plan.environment_fingerprint,
            parent_flow_id=execution_config.parent_flow_id,
            child_flow_ids=execution_config.child_flow_ids or (),
            tenant_id=resolved_flow.manifest.tenant_id,
            artifact_store=store,
            trace_recorder=trace_recorder,
            mode=execution_config.mode,
            verification_policy=execution_config.verification_policy,
            observers=execution_config.observers or (),
            budget=BudgetState(execution_config.budget),
            entropy=lifecycle,
            execution_store=execution_config.execution_store,
            run_id=run_id,
            resume_from_step_index=resume_from_step_index,
            starting_event_index=starting_event_index,
            starting_evidence_index=starting_evidence_index,
            starting_tool_invocation_index=starting_tool_invocation_index,
            starting_entropy_index=starting_entropy_index,
            initial_claim_ids=initial_claim_ids,
            initial_artifacts=initial_artifacts,
            initial_evidence=initial_evidence,
            initial_tool_invocations=initial_tool_invocations,
            _step_evidence={},
            _step_artifacts={},
            observed_run=execution_config.observed_run,
            strict_determinism=execution_config.strict_determinism,
        )
        return PreparedFlow(
            resolved_flow=resolved_flow,
            config=execution_config,
            context=context,
            strategy=strategy,
            run_id=run_id,
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
