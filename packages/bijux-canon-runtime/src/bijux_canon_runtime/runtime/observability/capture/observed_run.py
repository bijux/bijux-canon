# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for runtime/observability/capture/observed_run.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.reasoning_bundle import ReasoningBundle


@dataclass(frozen=True)
class ObservedRun:
    """ObservedRun is not a replay artifact and must never be used to validate determinism because it lacks the persisted contract boundary."""

    trace: ExecutionTrace
    artifacts: list[Artifact]
    evidence: list[RetrievedEvidence]
    reasoning_bundles: list[ReasoningBundle]


__all__ = ["ObservedRun"]
