# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/context.py."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING

from agentic_flows.core.authority import AuthorityToken
from agentic_flows.runtime.artifact_store import ArtifactStore
from agentic_flows.runtime.budget import BudgetState
from agentic_flows.runtime.observability.capture.hooks import RuntimeObserver
from agentic_flows.runtime.observability.capture.observed_run import ObservedRun
from agentic_flows.runtime.observability.capture.trace_recorder import TraceRecorder
from agentic_flows.runtime.orchestration.non_determinism_lifecycle import (
    NonDeterminismLifecycle,
)
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.model.verification.verification import VerificationPolicy
from agentic_flows.spec.ontology import EntropyMagnitude
from agentic_flows.spec.ontology.ids import (
    ClaimID,
    EnvironmentFingerprint,
    FlowID,
    RunID,
    TenantID,
)
from agentic_flows.spec.ontology.public import EntropySource

if TYPE_CHECKING:
    from agentic_flows.runtime.observability.storage.execution_store_protocol import (
        ExecutionWriteStoreProtocol,
    )


class RunMode(str, Enum):
    """Execution mode; misuse breaks mode-specific guarantees."""

    PLAN = "plan"
    DRY_RUN = "dry-run"
    LIVE = "live"
    OBSERVE = "observe"
    UNSAFE = "unsafe"


@dataclass(frozen=True)
class ExecutionContext:
    """Behavioral contract for ExecutionContext."""

    authority: AuthorityToken
    seed: str | None
    environment_fingerprint: EnvironmentFingerprint
    parent_flow_id: FlowID | None
    child_flow_ids: tuple[FlowID, ...]
    tenant_id: TenantID
    artifact_store: ArtifactStore
    trace_recorder: TraceRecorder
    mode: RunMode
    verification_policy: VerificationPolicy | None
    observers: tuple[RuntimeObserver, ...]
    budget: BudgetState
    entropy: NonDeterminismLifecycle
    execution_store: ExecutionWriteStoreProtocol | None
    run_id: RunID | None
    resume_from_step_index: int
    starting_event_index: int
    starting_evidence_index: int
    starting_tool_invocation_index: int
    starting_entropy_index: int
    initial_claim_ids: tuple[ClaimID, ...]
    initial_artifacts: list[Artifact]
    initial_evidence: list[RetrievedEvidence]
    initial_tool_invocations: list[ToolInvocation]
    _step_evidence: dict[int, tuple[RetrievedEvidence, ...]]
    _step_artifacts: dict[int, tuple[Artifact, ...]]
    strict_determinism: bool = False
    observed_run: ObservedRun | None = None
    _cancelled: bool = False

    def record_evidence(
        self, step_index: int, evidence: list[RetrievedEvidence]
    ) -> None:
        """Execute record_evidence and enforce its contract."""
        self._step_evidence[step_index] = tuple(evidence)

    def record_artifacts(self, step_index: int, artifacts: list[Artifact]) -> None:
        """Execute record_artifacts and enforce its contract."""
        for artifact in artifacts:
            self.artifact_store.load(artifact.artifact_id, tenant_id=self.tenant_id)
        self._step_artifacts[step_index] = tuple(artifacts)

    def evidence_for_step(self, step_index: int) -> tuple[RetrievedEvidence, ...]:
        """Execute evidence_for_step and enforce its contract."""
        return self._step_evidence.get(step_index, ())

    def artifacts_for_step(self, step_index: int) -> tuple[Artifact, ...]:
        """Execute artifacts_for_step and enforce its contract."""
        return self._step_artifacts.get(step_index, ())

    def recorded_steps(self) -> tuple[int, ...]:
        """Execute recorded_steps and enforce its contract."""
        return tuple(self._step_artifacts.keys())

    def consume_budget(
        self,
        *,
        steps: int = 0,
        tokens: int = 0,
        artifacts: int = 0,
        trace_events: int = 0,
    ) -> None:
        """Execute consume_budget and enforce its contract."""
        self.budget.consume(steps=steps, tokens=tokens, artifacts=artifacts)
        if trace_events:
            self.budget.consume_trace_events(trace_events)

    def start_step_budget(self) -> None:
        """Execute start_step_budget and enforce its contract."""
        self.budget.start_step()

    def consume_step_artifacts(self, artifacts: int) -> None:
        """Execute consume_step_artifacts and enforce its contract."""
        self.budget.consume_step_artifacts(artifacts)

    def consume_evidence_budget(self, evidence_items: int) -> None:
        """Execute consume_evidence_budget and enforce its contract."""
        self.budget.consume_evidence(evidence_items)

    def record_entropy(
        self,
        *,
        source: EntropySource,
        magnitude: EntropyMagnitude,
        description: str,
        step_index: int | None,
        nondeterminism_source: NonDeterminismSource,
    ) -> None:
        """Execute record_entropy and enforce its contract."""
        self.entropy.record(
            tenant_id=self.tenant_id,
            source=source,
            magnitude=magnitude,
            description=description,
            step_index=step_index,
            nondeterminism_source=nondeterminism_source,
        )

    def entropy_usage(self) -> tuple[EntropyUsage, ...]:
        """Execute entropy_usage and enforce its contract."""
        return self.entropy.usage()

    def cancel(self) -> None:
        """Execute cancel and enforce its contract."""
        object.__setattr__(self, "_cancelled", True)

    def is_cancelled(self) -> bool:
        """Execute is_cancelled and enforce its contract."""
        return object.__getattribute__(self, "_cancelled")


__all__ = ["RunMode"]
