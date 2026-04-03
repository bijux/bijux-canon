# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/storage/execution_store_protocol.py."""

from __future__ import annotations

from typing import Protocol

from agentic_flows.runtime.context import RunMode
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.execution_steps import ExecutionSteps
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.ontology.ids import ClaimID, RunID, TenantID


class ExecutionWriteStoreProtocol(Protocol):
    """Write store protocol; misuse breaks persistence guarantees."""

    def begin_run(
        self,
        *,
        plan: ExecutionSteps,
        mode: RunMode,
    ) -> RunID:
        """Execute begin_run and enforce its contract."""
        ...

    def finalize_run(self, *, run_id: RunID, trace: ExecutionTrace) -> None:
        """Execute finalize_run and enforce its contract."""
        ...

    def save_run(
        self,
        *,
        trace: ExecutionTrace | None,
        plan: ExecutionSteps,
        mode: RunMode,
    ) -> RunID:
        """Execute save_run and enforce its contract."""
        ...

    def save_steps(
        self, *, run_id: RunID, tenant_id: TenantID, plan: ExecutionSteps
    ) -> None:
        """Execute save_steps and enforce its contract."""
        ...

    def save_checkpoint(
        self,
        *,
        run_id: RunID,
        tenant_id: TenantID,
        step_index: int,
        event_index: int,
    ) -> None:
        """Execute save_checkpoint and enforce its contract."""
        ...

    def save_events(
        self,
        *,
        run_id: RunID,
        tenant_id: TenantID,
        events: tuple[ExecutionEvent, ...],
    ) -> None:
        """Execute save_events and enforce its contract."""
        ...

    def save_artifacts(self, *, run_id: RunID, artifacts: list[Artifact]) -> None:
        """Execute save_artifacts and enforce its contract."""
        ...

    def append_evidence(
        self,
        *,
        run_id: RunID,
        evidence: list[RetrievedEvidence],
        starting_index: int,
    ) -> None:
        """Execute append_evidence and enforce its contract."""
        ...

    def append_entropy_usage(
        self,
        *,
        run_id: RunID,
        usage: tuple[EntropyUsage, ...],
        starting_index: int,
    ) -> None:
        """Execute append_entropy_usage and enforce its contract."""
        ...

    def append_tool_invocations(
        self,
        *,
        run_id: RunID,
        tenant_id: TenantID,
        tool_invocations: tuple[ToolInvocation, ...],
        starting_index: int,
    ) -> None:
        """Execute append_tool_invocations and enforce its contract."""
        ...

    def append_claim_ids(
        self, *, run_id: RunID, tenant_id: TenantID, claim_ids: tuple[ClaimID, ...]
    ) -> None:
        """Execute append_claim_ids and enforce its contract."""
        ...

    def register_dataset(self, dataset: DatasetDescriptor) -> None:
        """Execute register_dataset and enforce its contract."""
        ...


class ExecutionReadStoreProtocol(Protocol):
    """Read store protocol; misuse breaks replay guarantees."""

    def load_trace(self, run_id: RunID, *, tenant_id: TenantID) -> ExecutionTrace:
        """Execute load_trace and enforce its contract."""
        ...

    def load_events(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[ExecutionEvent, ...]:
        """Execute load_events and enforce its contract."""
        ...

    def load_artifacts(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[Artifact, ...]:
        """Execute load_artifacts and enforce its contract."""
        ...

    def load_evidence(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[RetrievedEvidence, ...]:
        """Execute load_evidence and enforce its contract."""
        ...

    def load_tool_invocations(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[ToolInvocation, ...]:
        """Execute load_tool_invocations and enforce its contract."""
        ...

    def load_entropy_usage(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[EntropyUsage, ...]:
        """Execute load_entropy_usage and enforce its contract."""
        ...

    def load_claim_ids(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[ClaimID, ...]:
        """Execute load_claim_ids and enforce its contract."""
        ...

    def load_checkpoint(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> tuple[int, int] | None:
        """Execute load_checkpoint and enforce its contract."""
        ...

    def load_replay_envelope(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> ReplayEnvelope:
        """Execute load_replay_envelope and enforce its contract."""
        ...

    def load_dataset_descriptor(
        self, run_id: RunID, *, tenant_id: TenantID
    ) -> DatasetDescriptor:
        """Execute load_dataset_descriptor and enforce its contract."""
        ...


__all__ = ["ExecutionReadStoreProtocol", "ExecutionWriteStoreProtocol"]
