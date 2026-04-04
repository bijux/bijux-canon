# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for runtime/execution/step_executor.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.model.artifact.artifact import Artifact
from bijux_canon_runtime.model.artifact.retrieved_evidence import RetrievedEvidence
from bijux_canon_runtime.model.execution.execution_trace import ExecutionTrace
from bijux_canon_runtime.model.reasoning.bundle import ReasoningBundle
from bijux_canon_runtime.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from bijux_canon_runtime.model.verification.verification_result import (
    VerificationResult,
)


@dataclass(frozen=True)
class ExecutionOutcome:
    """Execution outcome; misuse breaks result integrity."""

    trace: ExecutionTrace
    artifacts: list[Artifact]
    evidence: list[RetrievedEvidence]
    reasoning_bundles: list[ReasoningBundle]
    verification_results: list[VerificationResult]
    verification_arbitrations: list[VerificationArbitration]


__all__ = ["ExecutionOutcome"]
