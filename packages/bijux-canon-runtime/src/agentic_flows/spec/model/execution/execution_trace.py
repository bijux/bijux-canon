# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/model/execution/execution_trace.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.model.execution.replay_envelope import ReplayEnvelope
from agentic_flows.spec.model.identifiers.execution_event import ExecutionEvent
from agentic_flows.spec.model.identifiers.tool_invocation import ToolInvocation
from agentic_flows.spec.ontology import (
    DeterminismLevel,
    EntropyExhaustionAction,
    FlowState,
)
from agentic_flows.spec.ontology.ids import (
    ClaimID,
    EnvironmentFingerprint,
    FlowID,
    PlanHash,
    PolicyFingerprint,
    ResolverID,
    TenantID,
)
from agentic_flows.spec.ontology.public import ReplayAcceptability, ReplayMode


@dataclass(frozen=True)
class ExecutionTrace:
    """Immutable after finalize; any post-finalize field mutation or event/tool/evidence edits are forbidden."""

    spec_version: str
    flow_id: FlowID
    tenant_id: TenantID
    parent_flow_id: FlowID | None
    child_flow_ids: tuple[FlowID, ...]
    flow_state: FlowState
    determinism_level: DeterminismLevel
    replay_acceptability: ReplayAcceptability
    dataset: DatasetDescriptor
    replay_envelope: ReplayEnvelope
    allow_deprecated_datasets: bool
    environment_fingerprint: EnvironmentFingerprint
    plan_hash: PlanHash
    verification_policy_fingerprint: PolicyFingerprint | None
    resolver_id: ResolverID
    events: tuple[ExecutionEvent, ...]
    tool_invocations: tuple[ToolInvocation, ...]
    entropy_usage: tuple[EntropyUsage, ...]
    claim_ids: tuple[ClaimID, ...]
    contradiction_count: int
    arbitration_decision: str
    finalized: bool
    replay_mode: ReplayMode = ReplayMode.STRICT
    entropy_exhausted: bool = False
    entropy_exhaustion_action: EntropyExhaustionAction | None = None
    non_certifiable: bool = False

    def finalize(self) -> ExecutionTrace:
        """Execute finalize and enforce its contract."""
        if object.__getattribute__(self, "finalized"):
            raise RuntimeError("ExecutionTrace already finalized")
        object.__setattr__(self, "finalized", True)
        return self

    def __getattribute__(self, name: str):
        """Internal helper; not part of the public API."""
        if name in {
            "finalize",
            "__class__",
            "__dict__",
            "__getattribute__",
            "__setattr__",
        }:
            return object.__getattribute__(self, name)
        if not object.__getattribute__(self, "finalized"):
            raise RuntimeError("ExecutionTrace accessed before finalization")
        return object.__getattribute__(self, name)

    def __repr__(self) -> str:
        """Internal helper; not part of the public API."""
        summary = (
            f"flow_id={self.flow_id}",
            f"tenant_id={self.tenant_id}",
            f"flow_state={self.flow_state.value}",
            f"determinism_level={self.determinism_level.value}",
            f"replay_acceptability={self.replay_acceptability.value}",
            f"dataset_hash={self.dataset.dataset_hash}",
            f"plan_hash={self.plan_hash}",
            f"event_count={len(self.events)}",
            f"tool_invocation_count={len(self.tool_invocations)}",
            f"entropy_usage_count={len(self.entropy_usage)}",
            f"claim_id_count={len(self.claim_ids)}",
            f"contradiction_count={self.contradiction_count}",
            f"arbitration_decision={self.arbitration_decision}",
            f"finalized={self.finalized}",
            f"replay_mode={self.replay_mode.value}",
            f"entropy_exhausted={self.entropy_exhausted}",
            f"non_certifiable={self.non_certifiable}",
        )
        return f"ExecutionTrace({', '.join(summary)})"

    def __str__(self) -> str:
        """Internal helper; not part of the public API."""
        return self.__repr__()


__all__ = ["ExecutionTrace"]
