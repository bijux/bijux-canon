# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Network-free adapters that replay immutable recorded step outputs."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.execution.request_plan import (
    ConcreteDagStep,
    DagOperation,
)
from bijux_canon_runtime.runtime.execution.operation_dispatcher import (
    StepDispatchContext,
    StepDispatchError,
    StepOutputArtifact,
)
from bijux_canon_runtime.runtime.inspection import InspectedDagStep
from bijux_canon_runtime.runtime.persistence.payload_store import ArtifactPayloadStore


@dataclass(frozen=True, slots=True)
class RecordedReplayAdapter:
    """Return verified source outputs for one operation without external calls."""

    operation: DagOperation
    source_steps: dict[str, InspectedDagStep]
    store: ArtifactPayloadStore
    adapter_id: str = "bijux-canon-runtime:recorded-replay:v1"
    adapter_version: str = "1.0"

    def execute(
        self,
        step: ConcreteDagStep,
        upstream_artifacts: tuple[StepOutputArtifact, ...],
        context: StepDispatchContext,
    ) -> tuple[StepOutputArtifact, ...]:
        """Load exact source artifacts and preserve their contract identities."""
        context.raise_if_cancelled()
        source = self.source_steps.get(step.step_id)
        if source is None or source.operation != self.operation.value:
            raise StepDispatchError("recorded replay step is unresolved")
        outputs = tuple(
            StepOutputArtifact(
                contract_id=self.store.load(artifact_id).descriptor.schema_id,
                producer_step_id=step.step_id,
                producer_operation=step.operation,
                artifact=self.store.load(artifact_id),
            )
            for artifact_id in source.output_artifact_ids
        )
        if not outputs:
            raise StepDispatchError("recorded replay step has no successful outputs")
        expected_dependencies = tuple(
            sorted(item.artifact_id for item in upstream_artifacts)
        )
        if any(
            item.artifact.descriptor.dependencies != expected_dependencies
            for item in outputs
        ):
            raise StepDispatchError("recorded replay dependency identity changed")
        context.raise_if_cancelled()
        return outputs


__all__ = ["RecordedReplayAdapter"]
