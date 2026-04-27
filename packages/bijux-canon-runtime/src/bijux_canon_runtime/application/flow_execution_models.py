"""Execution models shared across flow preparation and execution."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Protocol

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.command_modes import run_mode_for_command
from bijux_canon_runtime.model.execution.execution_plan import ExecutionPlan
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.model.identifiers.tool_invocation import ToolInvocation
from bijux_canon_runtime.model.policy.non_determinism_policy import (
    NonDeterminismPolicy,
)
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification import VerificationPolicy
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)
from bijux_canon_runtime.observability.capture.hooks import RuntimeObserver
from bijux_canon_runtime.observability.capture.observed_run import ObservedRun
from bijux_canon_runtime.observability.capture.trace_recorder import TraceRecorder
from bijux_canon_runtime.observability.storage.execution_store_protocol import (
    ExecutionReadStoreProtocol,
    ExecutionWriteStoreProtocol,
)
from bijux_canon_runtime.ontology import DeterminismLevel
from bijux_canon_runtime.ontology.ids import ClaimID, FlowID, RunID
from bijux_canon_runtime.runtime.artifact_store import ArtifactStore
from bijux_canon_runtime.runtime.budget import ExecutionBudget
from bijux_canon_runtime.runtime.context import ExecutionContext
from bijux_canon_runtime.runtime.execution.step_executor import ExecutionOutcome

if TYPE_CHECKING:
    from bijux_canon_runtime.model.flows.manifest import FlowManifest


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
        """Build config from the command-line command name."""
        return cls(
            mode=run_mode_for_command(command),
            determinism_level=DeterminismLevel.STRICT,
        )

    def for_manifest(self, manifest: FlowManifest) -> ExecutionConfig:
        """Return a copy aligned to the manifest determinism contract."""
        return ExecutionConfig(
            mode=self.mode,
            determinism_level=manifest.determinism_level,
            verification_policy=self.verification_policy,
            non_determinism_policy=self.non_determinism_policy,
            artifact_store=self.artifact_store,
            execution_store=self.execution_store,
            execution_read_store=self.execution_read_store,
            budget=self.budget,
            observed_run=self.observed_run,
            parent_flow_id=self.parent_flow_id,
            child_flow_ids=self.child_flow_ids,
            observers=self.observers,
            resume_run_id=self.resume_run_id,
            strict_determinism=self.strict_determinism,
        )


@dataclass(frozen=True)
class PreparedFlow:
    """Prepared flow; misuse breaks execution invariants."""

    resolved_flow: ExecutionPlan
    config: ExecutionConfig
    context: ExecutionContext
    strategy: _ExecutionStrategy
    run_id: RunID


@dataclass
class ExecutionStartState:
    """Execution bootstrap state; not part of the public API."""

    run_id: RunID | None
    resume_from_step_index: int = -1
    starting_event_index: int = 0
    starting_evidence_index: int = 0
    starting_tool_invocation_index: int = 0
    starting_entropy_index: int = 0
    initial_claim_ids: tuple[ClaimID, ...] = ()
    initial_artifacts: list[Artifact] = field(default_factory=list)
    initial_evidence: list[RetrievedEvidence] = field(default_factory=list)
    initial_tool_invocations: list[ToolInvocation] = field(default_factory=list)
    trace_recorder: TraceRecorder = field(default_factory=TraceRecorder)


class _ExecutionStrategy(Protocol):
    """Execution strategy contract for prepared flows."""

    def execute(
        self, plan: ExecutionPlan, context: ExecutionContext
    ) -> ExecutionOutcome:
        """Execute a prepared plan within the given context."""
        ...


__all__ = [
    "ExecutionConfig",
    "ExecutionStartState",
    "FlowRunResult",
    "PreparedFlow",
]
