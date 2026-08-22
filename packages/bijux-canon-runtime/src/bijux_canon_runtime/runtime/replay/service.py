# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Runtime-owned execution service for linked immutable replay attempts."""

from __future__ import annotations

from collections.abc import Callable

from bijux_canon_runtime.model.execution.request_plan import DagOperation
from bijux_canon_runtime.model.execution.run_identity import (
    AttemptRelation,
    ExecutionAttemptIdentity,
)
from bijux_canon_runtime.ontology.ids import RequestID, RunID
from bijux_canon_runtime.ontology.public import ReplayMode
from bijux_canon_runtime.runtime.execution.dag_scheduler import (
    ArtifactTransitionJournal,
    DependencyAwareScheduler,
    SchedulerPolicy,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    OperationDispatcher,
)
from bijux_canon_runtime.runtime.execution.runtime_event_ledger import (
    RuntimeEventLedger,
)
from bijux_canon_runtime.runtime.inspection import (
    InspectedAttempt,
    InspectedEventKind,
    InspectedRunStatus,
    RuntimeRunInspection,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.inspection.parsing import (
    required_dict,
    required_object,
    required_string,
)
from bijux_canon_runtime.runtime.persistence.filesystem_payload_store import (
    AtomicFilesystemArtifactPayloadStore,
)
from bijux_canon_runtime.runtime.replay.models import (
    ReplayNetworkPolicy,
    ReplayStepIdentityComparison,
    RuntimeReplayComparison,
    RuntimeReplayError,
    RuntimeReplayOutcome,
    RuntimeReplayPolicy,
)
from bijux_canon_runtime.runtime.replay.plan_reconstruction import (
    reconstruct_replay_plan,
)
from bijux_canon_runtime.runtime.replay.recorded_adapter import (
    RecordedReplayAdapter,
)


class RuntimeReplayService:
    """Reconstruct, execute, persist, and compare one linked replay attempt."""

    def __init__(self, store: AtomicFilesystemArtifactPayloadStore) -> None:
        self._store = store
        self._inspector = RuntimeRunInspector(store)

    def replay(
        self,
        *,
        run_id: str,
        source_attempt_id: str,
        request_id: RequestID,
        process_id: str,
        policy: RuntimeReplayPolicy,
        dispatcher: OperationDispatcher | None = None,
        scheduler_policy: SchedulerPolicy | None = None,
        is_cancelled: Callable[[], bool] | None = None,
        deadline_monotonic: float | None = None,
    ) -> RuntimeReplayOutcome:
        """Create or idempotently resolve a replay under explicit authority."""
        current = self._inspector.inspect(run_id)
        source = self._inspector.inspect(run_id, attempt_id=source_attempt_id)
        if source.status is not InspectedRunStatus.COMPLETED:
            raise RuntimeReplayError("only a completed source attempt can be replayed")
        existing = next(
            (item for item in current.attempts if item.request_id == str(request_id)),
            None,
        )
        if existing is not None:
            return self._reuse_existing(
                source=source,
                existing=existing,
                policy=policy,
            )
        if current.selected_attempt_id != source_attempt_id:
            raise RuntimeReplayError("a replay must extend the latest persisted attempt")
        source_identity = _attempt_identity(
            next(
                item
                for item in source.attempts
                if item.attempt_id == source_attempt_id
            ),
            run_id=run_id,
        )
        replay_identity = ExecutionAttemptIdentity.replay_persisted(
            request_id=request_id,
            source=source_identity,
            process_id=process_id,
        )
        reconstruction = reconstruct_replay_plan(
            source,
            request_id=request_id,
            policy=policy,
        )
        plan = reconstruction.plan
        selected_dispatcher = self._dispatcher(
            source=source,
            policy=policy,
            plan_operations=tuple(step.operation for step in plan.steps),
            live_dispatcher=dispatcher,
        )
        schedule_policy = scheduler_policy or SchedulerPolicy.for_plan(
            plan,
            max_workers=4,
            max_resource_units=4,
        )
        journal = ArtifactTransitionJournal(
            store=self._store,
            plan_sha256=plan.plan_sha256,
        )
        ledger = RuntimeEventLedger(
            store=self._store,
            plan=plan,
            attempt=replay_identity,
            execution_metadata={"replay_policy": _policy_record(policy)},
        )
        schedule = DependencyAwareScheduler(
            dispatcher=selected_dispatcher,
            policy=schedule_policy,
            journal=journal,
            events=ledger,
        ).run(
            plan,
            is_cancelled=is_cancelled,
            deadline_monotonic=deadline_monotonic,
        )
        replay = self._inspector.inspect(
            run_id,
            attempt_id=replay_identity.attempt_id,
        )
        return RuntimeReplayOutcome(
            source=source,
            replay=replay,
            policy=policy,
            comparison=_compare(source, replay, policy),
            reused=False,
            transition_artifact_ids=schedule.transition_artifact_ids,
        )

    def _reuse_existing(
        self,
        *,
        source: RuntimeRunInspection,
        existing: InspectedAttempt,
        policy: RuntimeReplayPolicy,
    ) -> RuntimeReplayOutcome:
        if (
            existing.relation != AttemptRelation.REPLAY.value
            or existing.source_attempt_id != source.selected_attempt_id
        ):
            raise RuntimeReplayError(
                "replay request identity is already bound to another attempt"
            )
        replay = self._inspector.inspect(
            source.run_id,
            attempt_id=existing.attempt_id,
        )
        if _inspection_policy(replay) != _policy_record(policy):
            raise RuntimeReplayError(
                "replay request identity is already bound to another policy"
            )
        return RuntimeReplayOutcome(
            source=source,
            replay=replay,
            policy=policy,
            comparison=_compare(source, replay, policy),
            reused=True,
            transition_artifact_ids=(),
        )

    def _dispatcher(
        self,
        *,
        source: RuntimeRunInspection,
        policy: RuntimeReplayPolicy,
        plan_operations: tuple[DagOperation, ...],
        live_dispatcher: OperationDispatcher | None,
    ) -> OperationDispatcher:
        providers = {
            value
            for artifact in source.artifacts
            if artifact.schema_id == "bijux.runtime.execution-manifest.v1"
            and isinstance(artifact.json_value, dict)
            for value in _manifest_providers(artifact.json_value)
        }
        if policy.network_policy is ReplayNetworkPolicy.PERMITTED:
            if not providers.issubset(policy.provider_allowlist):
                raise RuntimeReplayError(
                    "replay provider is outside the explicit allowlist"
                )
            if live_dispatcher is None:
                raise RuntimeReplayError(
                    "network-permitted replay requires an explicit live dispatcher"
                )
            return live_dispatcher
        if live_dispatcher is not None:
            raise RuntimeReplayError("offline replay cannot accept a live dispatcher")
        source_steps = {step.step_id: step for step in source.steps}
        return OperationDispatcher(
            RecordedReplayAdapter(operation, source_steps, self._store)
            for operation in dict.fromkeys(plan_operations)
        )


def _attempt_identity(
    attempt: InspectedAttempt,
    *,
    run_id: str,
) -> ExecutionAttemptIdentity:
    return ExecutionAttemptIdentity(
        attempt_id=attempt.attempt_id,
        run_id=RunID(run_id),
        request_id=RequestID(attempt.request_id),
        attempt_number=attempt.attempt_number,
        relation=AttemptRelation(attempt.relation),
        source_attempt_id=attempt.source_attempt_id,
        supersedes_attempt_id=attempt.supersedes_attempt_id,
        retry_id=attempt.retry_id,
        replay_id=attempt.replay_id,
        process_id=attempt.process_id,
    )


def _policy_record(policy: RuntimeReplayPolicy) -> dict[str, object]:
    return {
        "network_policy": policy.network_policy.value,
        "provider_allowlist": list(policy.provider_allowlist),
        "replay_mode": policy.replay_mode.value,
        "tolerance": {
            "max_duration_delta_ms": policy.tolerance.max_duration_delta_ms,
            "max_duration_ratio": policy.tolerance.max_duration_ratio,
        },
    }


def _inspection_policy(inspection: RuntimeRunInspection) -> dict[str, object]:
    for artifact in inspection.artifacts:
        if (
            artifact.schema_id != "bijux.runtime.execution-manifest.v1"
            or not isinstance(artifact.json_value, dict)
        ):
            continue
        attempt = required_object(artifact.json_value, "attempt")
        if required_string(attempt, "attempt_id") != inspection.selected_attempt_id:
            continue
        metadata = required_object(artifact.json_value, "execution_metadata")
        return required_object(metadata, "replay_policy")
    raise RuntimeReplayError("replay policy metadata is unavailable")


def _manifest_providers(manifest: dict[str, object]) -> tuple[str, ...]:
    plan = required_object(manifest, "plan")
    providers: list[str] = []
    raw_steps = plan.get("steps")
    if not isinstance(raw_steps, list):
        raise RuntimeReplayError("source replay plan steps are invalid")
    for raw_step in raw_steps:
        step = required_dict(raw_step, "plan step")
        provider = required_object(step, "inputs").get("provider")
        if provider is not None:
            if not isinstance(provider, str) or not provider.strip():
                raise RuntimeReplayError("source replay provider is invalid")
            providers.append(provider)
    return tuple(dict.fromkeys(providers))


def _compare(
    source: RuntimeRunInspection,
    replay: RuntimeRunInspection,
    policy: RuntimeReplayPolicy,
) -> RuntimeReplayComparison:
    source_steps = {step.step_id: step for step in source.steps}
    replay_steps = {step.step_id: step for step in replay.steps}
    dag_equal = {
        key: (
            value.operation,
            value.depends_on,
            value.input_contract_ids,
            value.output_contract_ids,
        )
        for key, value in source_steps.items()
    } == {
        key: (
            value.operation,
            value.depends_on,
            value.input_contract_ids,
            value.output_contract_ids,
        )
        for key, value in replay_steps.items()
    }
    comparisons = tuple(
        ReplayStepIdentityComparison(
            step_id=step_id,
            operation=source_step.operation,
            deterministic=source_step.operation not in {"reason", "agent"},
            source_output_artifact_ids=source_step.output_artifact_ids,
            replay_output_artifact_ids=(
                replay_steps[step_id].output_artifact_ids
                if step_id in replay_steps
                else ()
            ),
            identities_equal=(
                step_id in replay_steps
                and source_step.output_artifact_ids
                == replay_steps[step_id].output_artifact_ids
            ),
        )
        for step_id, source_step in source_steps.items()
    )
    exact = all(item.identities_equal for item in comparisons)
    deterministic = all(
        item.identities_equal for item in comparisons if item.deterministic
    )
    source_duration = _duration(source)
    replay_duration = _duration(replay)
    delta = abs(replay_duration - source_duration)
    if source_duration == replay_duration == 0:
        ratio: float | None = 1.0
    elif min(source_duration, replay_duration) == 0:
        ratio = None
    else:
        ratio = max(source_duration, replay_duration) / min(
            source_duration, replay_duration
        )
    within_tolerance = (
        delta <= policy.tolerance.max_duration_delta_ms
        and (ratio is None or ratio <= policy.tolerance.max_duration_ratio)
    )
    completed = replay.status is InspectedRunStatus.COMPLETED
    semantics_accepted = completed and dag_equal
    timing_accepted = (
        within_tolerance
        or policy.network_policy is not ReplayNetworkPolicy.PERMITTED
    )
    if policy.replay_mode is ReplayMode.STRICT:
        accepted = semantics_accepted and exact and timing_accepted
    elif policy.replay_mode is ReplayMode.BOUNDED:
        accepted = semantics_accepted and deterministic and timing_accepted
    else:
        accepted = completed
    return RuntimeReplayComparison(
        dag_equal=dag_equal,
        exact_artifact_identities=exact,
        deterministic_artifact_identities=deterministic,
        source_duration_ms=source_duration,
        replay_duration_ms=replay_duration,
        duration_delta_ms=delta,
        duration_ratio=ratio,
        duration_within_tolerance=within_tolerance,
        accepted=accepted,
        steps=comparisons,
    )


def _duration(inspection: RuntimeRunInspection) -> float:
    terminal = {
        InspectedEventKind.COMPLETED,
        InspectedEventKind.FAILED,
        InspectedEventKind.CANCELLED,
        InspectedEventKind.TIMED_OUT,
    }
    return sum(
        event.duration_ms or 0.0
        for event in inspection.events
        if event.event_kind in terminal
    )


__all__ = ["RuntimeReplayService"]
