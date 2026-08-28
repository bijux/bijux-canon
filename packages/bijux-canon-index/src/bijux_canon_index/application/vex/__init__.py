# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verified vector-execution application contracts."""

from .artifacts import (
    VexArtifactStore,
    VexCandidateRecord,
    VexExecutionArtifact,
    VexStoredArtifact,
)
from .policy import (
    VexExecutionBudget,
    VexExecutionObservation,
    VexPolicyDecision,
    VexPolicyMode,
    VexPolicyStatus,
    VexPolicyViolation,
    evaluate_vex_budget,
)
from .replay import (
    VexDriftKind,
    VexReplayComparison,
    VexReplayExecutor,
    VexReplayInput,
    VexReplayOutcome,
    compare_vex_artifacts,
    replay_vex_execution,
)
from .witnesses import (
    ExactSearchCandidate,
    ExactSearchWitness,
    build_exact_search_witness,
)

__all__ = [
    "ExactSearchCandidate",
    "ExactSearchWitness",
    "VexArtifactStore",
    "VexCandidateRecord",
    "VexDriftKind",
    "VexExecutionBudget",
    "VexExecutionArtifact",
    "VexExecutionObservation",
    "VexPolicyDecision",
    "VexPolicyMode",
    "VexPolicyStatus",
    "VexPolicyViolation",
    "VexReplayComparison",
    "VexReplayExecutor",
    "VexReplayInput",
    "VexReplayOutcome",
    "VexStoredArtifact",
    "build_exact_search_witness",
    "compare_vex_artifacts",
    "evaluate_vex_budget",
    "replay_vex_execution",
]
