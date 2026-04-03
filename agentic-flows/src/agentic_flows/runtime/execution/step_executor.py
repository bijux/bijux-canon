# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/execution/step_executor.py."""

from __future__ import annotations

from dataclasses import dataclass

from agentic_flows.spec.model.artifact.artifact import Artifact
from agentic_flows.spec.model.artifact.retrieved_evidence import RetrievedEvidence
from agentic_flows.spec.model.execution.execution_trace import ExecutionTrace
from agentic_flows.spec.model.reasoning_bundle import ReasoningBundle
from agentic_flows.spec.model.verification.verification_arbitration import (
    VerificationArbitration,
)
from agentic_flows.spec.model.verification.verification_result import VerificationResult


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
