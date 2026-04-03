# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

# Agent execution is the only place bijux-agent may be invoked.
# Allowed: seeded agent execution with explicit inputs and seeded randomness.
# Forbidden: I/O, network access, retrieval, vector search, reasoning, or memory writes.
"""Module definitions for runtime/execution/agent_executor.py."""

from __future__ import annotations

import hashlib
from typing import Any

import bijux_agent

from agentic_flows.runtime.context import ExecutionContext
from agentic_flows.runtime.execution.state_tracker import ExecutionStateTracker
from agentic_flows.runtime.observability.classification.seed import deterministic_seed
from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.execution.resolved_step import ResolvedStep
from agentic_flows.spec.ontology import (
    ArtifactScope,
    ArtifactType,
)
from agentic_flows.spec.ontology.ids import ArtifactID, ContentHash


class AgentExecutor:
    """Behavioral contract for AgentExecutor."""

    def __init__(self) -> None:
        """Internal helper; not part of the public API."""
        self._state_tracker: ExecutionStateTracker | None = None

    def execute(self, step: ResolvedStep, context: ExecutionContext) -> list[Artifact]:
        """Execute execute and enforce its contract."""
        if self._state_tracker is None:
            self._state_tracker = ExecutionStateTracker(context.seed)
        seed = deterministic_seed(step.step_index, step.inputs_fingerprint)
        if not hasattr(bijux_agent, "run"):
            raise RuntimeError("bijux_agent.run is required for agent execution")

        evidence = list(context.evidence_for_step(step.step_index))
        outputs = bijux_agent.run(
            agent_id=step.agent_invocation.agent_id,
            seed=seed,
            inputs_fingerprint=step.inputs_fingerprint,
            declared_outputs=step.agent_invocation.declared_outputs,
            evidence=evidence,
        )
        artifacts = self._artifacts_from_outputs(step, outputs, context)
        state_artifact = self._state_artifact(step, artifacts, context)
        artifacts.append(state_artifact)
        context.record_artifacts(step.step_index, artifacts)
        return artifacts

    def _artifacts_from_outputs(
        self,
        step: ResolvedStep,
        outputs: Any,
        context: ExecutionContext,
    ) -> list[Artifact]:
        """Internal helper; not part of the public API."""
        if not isinstance(outputs, list):
            raise ValueError("agent outputs must be a list")

        artifacts = []
        for entry in outputs:
            if not isinstance(entry, dict):
                raise ValueError("agent outputs must be dict entries")
            if (
                "artifact_id" not in entry
                or "artifact_type" not in entry
                or "content" not in entry
            ):
                raise ValueError("agent output missing required fields")

            content_hash = ContentHash(self._hash_content(entry["content"]))
            parent_artifacts = entry.get("parent_artifacts", [])
            if not isinstance(parent_artifacts, list):
                raise ValueError("parent_artifacts must be a list")

            artifact_type = ArtifactType(str(entry["artifact_type"]))
            artifacts.append(
                context.artifact_store.create(
                    spec_version="v1",
                    artifact_id=ArtifactID(str(entry["artifact_id"])),
                    tenant_id=context.tenant_id,
                    artifact_type=artifact_type,
                    producer="agent",
                    parent_artifacts=tuple(
                        ArtifactID(str(item)) for item in parent_artifacts
                    ),
                    content_hash=content_hash,
                    scope=ArtifactScope.WORKING,
                )
            )
        return artifacts

    def _state_artifact(
        self,
        step: ResolvedStep,
        artifacts: list[Artifact],
        context: ExecutionContext,
    ) -> Artifact:
        """Internal helper; not part of the public API."""
        state_hash = self._state_tracker.advance(step)
        return context.artifact_store.create(
            spec_version="v1",
            artifact_id=ArtifactID(f"state-{step.step_index}-{step.agent_id}"),
            tenant_id=context.tenant_id,
            artifact_type=ArtifactType.EXECUTOR_STATE,
            producer="agent",
            parent_artifacts=tuple(artifact.artifact_id for artifact in artifacts),
            content_hash=state_hash,
            scope=ArtifactScope.AUDIT,
        )

    @staticmethod
    def _hash_content(content: Any) -> str:
        """Internal helper; not part of the public API."""
        payload = str(content).encode("utf-8")
        return hashlib.sha256(payload).hexdigest()
