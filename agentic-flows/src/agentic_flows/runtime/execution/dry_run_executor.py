# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

# Dry-run exists to generate repeatable traces when inputs are fixed, without invoking any agent logic.
# It must remain intelligence-free: no tools, no network, no retrieval, no reasoning code.
# Forbidden: calling bijux-agent, bijux-rag, bijux-rar, bijux-vex, or any external side effects.
"""Module definitions for runtime/execution/dry_run_executor.py."""

from __future__ import annotations

from contextlib import suppress

from agentic_flows.core.authority import finalize_trace
from agentic_flows.runtime.context import ExecutionContext
from agentic_flows.runtime.execution.state_tracker import ExecutionStateTracker
from agentic_flows.runtime.execution.step_executor import ExecutionOutcome
from agentic_flows.runtime.observability.capture.time import utc_now_deterministic
from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
    fingerprint_policy,
)
from agentic_flows.runtime.orchestration.flow_boundary import enforce_flow_boundary
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.execution.execution_plan import ExecutionPlan
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
    CausalityTag,
)
from agentic_flows.spec.ontology.ids import ArtifactID, PolicyFingerprint, ResolverID
from agentic_flows.spec.ontology.public import EventType


def _causality_tag(event_type: EventType) -> CausalityTag:
    """Internal helper; not part of the public API."""
    return CausalityTag.AGENT


class DryRunExecutor:
    """Behavioral contract for DryRunExecutor."""

    def execute(
        self, plan: ExecutionPlan, context: ExecutionContext
    ) -> ExecutionOutcome:
        """Execute execute and enforce its contract."""
        steps_plan = plan.plan
        enforce_flow_boundary(steps_plan)
        recorder = context.trace_recorder
        event_index = 0
        artifacts: list[Artifact] = []
        state_tracker = ExecutionStateTracker(context.seed)

        for step in steps_plan.steps:
            context.start_step_budget()
            start_payload = {
                "event_type": EventType.STEP_START.value,
                "step_index": step.step_index,
                "agent_id": step.agent_id,
            }
            event = ExecutionEvent(
                spec_version="v1",
                event_index=event_index,
                step_index=step.step_index,
                event_type=EventType.STEP_START,
                causality_tag=_causality_tag(EventType.STEP_START),
                timestamp_utc=utc_now_deterministic(event_index),
                payload=start_payload,
                payload_hash=fingerprint_inputs(start_payload),
            )
            recorder.record(event, context.authority)
            for observer in context.observers:
                observer.on_event(event)
            with suppress(Exception):
                context.consume_budget(trace_events=1)
            event_index += 1
            try:
                context.consume_budget(steps=1)
            except Exception as exc:
                fail_payload = {
                    "event_type": EventType.STEP_FAILED.value,
                    "step_index": step.step_index,
                    "agent_id": step.agent_id,
                    "error": str(exc),
                }
                event = ExecutionEvent(
                    spec_version="v1",
                    event_index=event_index,
                    step_index=step.step_index,
                    event_type=EventType.STEP_FAILED,
                    causality_tag=_causality_tag(EventType.STEP_FAILED),
                    timestamp_utc=utc_now_deterministic(event_index),
                    payload=fail_payload,
                    payload_hash=fingerprint_inputs(fail_payload),
                )
                recorder.record(event, context.authority)
                for observer in context.observers:
                    observer.on_event(event)
                with suppress(Exception):
                    context.consume_budget(trace_events=1)
                event_index += 1
                break
            state_hash = state_tracker.advance(step)
            state_artifact = context.artifact_store.create(
                spec_version="v1",
                artifact_id=ArtifactID(f"state-{step.step_index}-{step.agent_id}"),
                tenant_id=context.tenant_id,
                artifact_type=ArtifactType.EXECUTOR_STATE,
                producer="agent",
                parent_artifacts=(),
                content_hash=state_hash,
                scope=ArtifactScope.AUDIT,
            )
            artifacts.append(state_artifact)
            context.consume_budget(artifacts=1)
            context.consume_step_artifacts(1)
            context.record_artifacts(step.step_index, [state_artifact])

            end_payload = {
                "event_type": EventType.STEP_END.value,
                "step_index": step.step_index,
                "agent_id": step.agent_id,
            }
            event = ExecutionEvent(
                spec_version="v1",
                event_index=event_index,
                step_index=step.step_index,
                event_type=EventType.STEP_END,
                causality_tag=_causality_tag(EventType.STEP_END),
                timestamp_utc=utc_now_deterministic(event_index),
                payload=end_payload,
                payload_hash=fingerprint_inputs(end_payload),
            )
            recorder.record(event, context.authority)
            for observer in context.observers:
                observer.on_event(event)
            with suppress(Exception):
                context.consume_budget(trace_events=1)
            event_index += 1

        resolver_id = ResolverID(
            self._resolver_id_from_metadata(steps_plan.resolution_metadata)
        )
        nondeterminism_verdict = context.entropy.verdict()
        trace = ExecutionTrace(
            spec_version="v1",
            flow_id=steps_plan.flow_id,
            tenant_id=steps_plan.tenant_id,
            parent_flow_id=context.parent_flow_id,
            child_flow_ids=context.child_flow_ids,
            flow_state=steps_plan.flow_state,
            determinism_level=steps_plan.determinism_level,
            replay_mode=steps_plan.replay_mode,
            replay_acceptability=steps_plan.replay_acceptability,
            dataset=steps_plan.dataset,
            replay_envelope=steps_plan.replay_envelope,
            allow_deprecated_datasets=steps_plan.allow_deprecated_datasets,
            environment_fingerprint=steps_plan.environment_fingerprint,
            plan_hash=steps_plan.plan_hash,
            verification_policy_fingerprint=(
                PolicyFingerprint(fingerprint_policy(context.verification_policy))
                if context.verification_policy is not None
                else None
            ),
            resolver_id=resolver_id,
            events=recorder.events(),
            tool_invocations=(),
            entropy_usage=context.entropy_usage(),
            claim_ids=(),
            contradiction_count=0,
            arbitration_decision="none",
            entropy_exhausted=nondeterminism_verdict.entropy_exhausted,
            entropy_exhaustion_action=nondeterminism_verdict.entropy_exhaustion_action,
            non_certifiable=nondeterminism_verdict.non_certifiable,
            finalized=False,
        )
        finalize_trace(trace)
        return ExecutionOutcome(
            trace=trace,
            artifacts=artifacts,
            evidence=[],
            reasoning_bundles=[],
            verification_results=[],
            verification_arbitrations=[],
        )

    @staticmethod
    def _resolver_id_from_metadata(metadata: tuple[tuple[str, str], ...]) -> str:
        """Internal helper; not part of the public API."""
        for key, value in metadata:
            if key == "resolver_id":
                return value
        raise ValueError("resolution_metadata missing resolver_id")
