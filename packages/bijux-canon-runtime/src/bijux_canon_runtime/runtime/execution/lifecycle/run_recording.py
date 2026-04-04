# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Recording helpers for execution runs."""

from __future__ import annotations

from contextlib import suppress
from dataclasses import dataclass

from bijux_canon_runtime.core.errors import NonDeterminismViolationError
from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.identifiers.execution_event import ExecutionEvent
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.observability.capture.time import utc_now_deterministic
from bijux_canon_runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from bijux_canon_runtime.ontology.ids import ClaimID
from bijux_canon_runtime.ontology.public import EventType
from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.runtime.execution.event_causality import event_causality_tag


@dataclass
class ExecutionRunRecorder:
    """Mutable recorder state for a single runtime execution."""

    context: ExecutionContext
    recorder: object
    tool_invocations: list[ToolInvocation]
    event_index: int
    evidence_index: int
    tool_invocation_index: int
    entropy_index: int
    entropy_checked_index: int

    @classmethod
    def from_context(
        cls,
        *,
        context: ExecutionContext,
        recorder: object,
        tool_invocations: list[ToolInvocation],
    ) -> ExecutionRunRecorder:
        """Create recorder state from the execution context offsets."""
        return cls(
            context=context,
            recorder=recorder,
            tool_invocations=tool_invocations,
            event_index=context.starting_event_index,
            evidence_index=context.starting_evidence_index,
            tool_invocation_index=context.starting_tool_invocation_index,
            entropy_index=context.starting_entropy_index,
            entropy_checked_index=context.starting_entropy_index,
        )

    def record_event(
        self, event_type: EventType, step_index: int, payload: dict[str, object]
    ) -> None:
        """Record an execution event and persist it when a store is present."""
        payload["event_type"] = event_type.value
        event = ExecutionEvent(
            spec_version="v1",
            event_index=self.event_index,
            step_index=step_index,
            event_type=event_type,
            causality_tag=event_causality_tag(event_type),
            timestamp_utc=utc_now_deterministic(self.event_index),
            payload=payload,
            payload_hash=fingerprint_inputs(payload),
        )
        self.recorder.record(event, self.context.authority)
        if self.context.execution_store is not None and self.context.run_id is not None:
            self.context.execution_store.save_events(
                run_id=self.context.run_id,
                tenant_id=self.context.tenant_id,
                events=(event,),
            )
        for observer in self.context.observers:
            observer.on_event(event)
        with suppress(Exception):
            self.context.consume_budget(trace_events=1)
        self.event_index += 1

    def record_tool_invocation(self, invocation: ToolInvocation) -> None:
        """Record tool invocation output and append it to persistence."""
        self.tool_invocations.append(invocation)
        if self.context.execution_store is not None and self.context.run_id is not None:
            self.context.execution_store.append_tool_invocations(
                run_id=self.context.run_id,
                tenant_id=self.context.tenant_id,
                tool_invocations=(invocation,),
                starting_index=self.tool_invocation_index,
            )
        self.tool_invocation_index += 1

    def record_evidence(self, items: list[RetrievedEvidence]) -> None:
        """Persist newly produced evidence."""
        if not items:
            return
        if self.context.execution_store is not None and self.context.run_id is not None:
            self.context.execution_store.append_evidence(
                run_id=self.context.run_id,
                evidence=items,
                starting_index=self.evidence_index,
            )
        self.evidence_index += len(items)

    def record_artifacts(self, items: list[Artifact]) -> None:
        """Persist newly produced artifacts."""
        if not items:
            return
        if self.context.execution_store is not None and self.context.run_id is not None:
            self.context.execution_store.save_artifacts(
                run_id=self.context.run_id,
                artifacts=items,
            )

    def record_claims(self, claims: tuple[ClaimID, ...]) -> None:
        """Persist newly produced claim ids."""
        if not claims:
            return
        if self.context.execution_store is not None and self.context.run_id is not None:
            self.context.execution_store.append_claim_ids(
                run_id=self.context.run_id,
                tenant_id=self.context.tenant_id,
                claim_ids=claims,
            )

    def flush_entropy_usage(self) -> None:
        """Persist entropy usage entries that have not been flushed yet."""
        if self.context.execution_store is None or self.context.run_id is None:
            return
        usage = self.context.entropy_usage()
        if len(usage) <= self.entropy_index:
            return
        new_entries = usage[self.entropy_index :]
        self.context.execution_store.append_entropy_usage(
            run_id=self.context.run_id,
            usage=new_entries,
            starting_index=self.entropy_index,
        )
        self.entropy_index = len(usage)

    def enforce_entropy_authorization(self) -> None:
        """Reject unauthorized entropy usage under strict determinism."""
        usage = self.context.entropy_usage()
        if len(usage) <= self.entropy_checked_index:
            return
        new_entries = usage[self.entropy_checked_index :]
        self.entropy_checked_index = len(usage)
        if not self.context.strict_determinism:
            return
        for entry in new_entries:
            if not entry.nondeterminism_source.authorized:
                raise NonDeterminismViolationError(
                    "entropy source used without explicit authorization"
                )

    def save_checkpoint(self, step_index: int) -> None:
        """Persist a checkpoint aligned to the latest recorded event."""
        if self.context.execution_store is None or self.context.run_id is None:
            return
        self.context.execution_store.save_checkpoint(
            run_id=self.context.run_id,
            tenant_id=self.context.tenant_id,
            step_index=step_index,
            event_index=self.event_index - 1,
        )


__all__ = ["ExecutionRunRecorder"]
