"""Ontology enums are frozen in v1; adding values requires a MAJOR bump, and reordering is forbidden."""
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from enum import StrEnum, auto

from agentic_flows.spec.ontology.ids import ActionID as Action
from agentic_flows.spec.ontology.ids import AgentID as Agent
from agentic_flows.spec.ontology.ids import ArtifactID as Artifact
from agentic_flows.spec.ontology.ids import EvidenceID as Evidence
from agentic_flows.spec.ontology.ids import FlowID as Flow
from agentic_flows.spec.ontology.ids import StepID as Step
from agentic_flows.spec.ontology.ids import ToolID as Tool


class ArtifactType(StrEnum):
    """Artifact types; mislabeling breaks artifact contracts."""

    FLOW_MANIFEST = "flow_manifest"
    EXECUTION_PLAN = "execution_plan"
    RESOLVED_STEP = "resolved_step"
    AGENT_INVOCATION = "agent_invocation"
    RETRIEVAL_REQUEST = "retrieval_request"
    RETRIEVED_EVIDENCE = "retrieved_evidence"
    REASONING_STEP = "reasoning_step"
    REASONING_CLAIM = "reasoning_claim"
    REASONING_BUNDLE = "reasoning_bundle"
    VERIFICATION_RULE = "verification_rule"
    VERIFICATION_RESULT = "verification_result"
    EXECUTION_EVENT = "execution_event"
    EXECUTION_TRACE = "execution_trace"
    EXECUTOR_STATE = "executor_state"


class ArtifactScope(StrEnum):
    """Artifact scope boundary; mis-scoping breaks isolation."""

    EPHEMERAL = "ephemeral"
    WORKING = "working"
    AUDIT = "audit"


class EventType(StrEnum):
    """Execution event types; misuse breaks trace invariants."""

    def _generate_next_value_(name, start, count, last_values):  # noqa: N805
        """Internal helper; not part of the public API."""
        return name

    STEP_START = auto()
    STEP_END = auto()
    STEP_FAILED = auto()
    RETRIEVAL_START = auto()
    RETRIEVAL_END = auto()
    RETRIEVAL_FAILED = auto()
    REASONING_START = auto()
    REASONING_END = auto()
    REASONING_FAILED = auto()
    VERIFICATION_START = auto()
    VERIFICATION_PASS = auto()
    VERIFICATION_FAIL = auto()
    VERIFICATION_ESCALATE = auto()
    VERIFICATION_ARBITRATION = auto()
    EXECUTION_INTERRUPTED = auto()
    HUMAN_INTERVENTION = auto()
    SEMANTIC_VIOLATION = auto()
    TOOL_CALL_START = auto()
    TOOL_CALL_END = auto()
    TOOL_CALL_FAIL = auto()


class CausalityTag(StrEnum):
    """Causality source tags; misuse breaks audit provenance."""

    AGENT = "agent"
    TOOL = "tool"
    DATASET = "dataset"
    ENVIRONMENT = "environment"
    HUMAN = "human"


class StepType(StrEnum):
    """Step types; misuse breaks step execution semantics."""

    AGENT = "agent"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    VERIFICATION = "verification"


class VerificationPhase(StrEnum):
    """Verification phases; misuse breaks gate ordering."""

    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"


class ArbitrationRule(StrEnum):
    """Arbitration rules; misuse breaks verification decisions."""

    UNANIMOUS = "unanimous"
    QUORUM = "quorum"
    STRICT_FIRST_FAILURE = "strict_first_failure"


class DeterminismLevel(StrEnum):
    """Determinism level; wrong value breaks enforcement."""

    STRICT = "strict"
    BOUNDED = "bounded"
    PROBABILISTIC = "probabilistic"
    UNCONSTRAINED = "unconstrained"


class DeterminismClass(StrEnum):
    """Determinism class; wrong value breaks classification."""

    STRUCTURAL = "structural"
    ENVIRONMENTAL = "environmental"
    STOCHASTIC = "stochastic"
    HUMAN = "human"
    EXTERNAL = "external"


class ReplayMode(StrEnum):
    """Replay modes; wrong value breaks replay governance."""

    STRICT = "strict"
    BOUNDED = "bounded"
    OBSERVATIONAL = "observational"


class FlowState(StrEnum):
    """Flow lifecycle state; misuse breaks flow governance."""

    DRAFT = "draft"
    VALIDATED = "validated"
    FROZEN = "frozen"
    DEPRECATED = "deprecated"


class DatasetState(StrEnum):
    """Dataset lifecycle state; misuse breaks dataset governance."""

    EXPERIMENTAL = "experimental"
    FROZEN = "frozen"
    DEPRECATED = "deprecated"


class ReplayAcceptability(StrEnum):
    """Replay acceptability; wrong value breaks replay contract."""

    EXACT_MATCH = "exact_match"
    INVARIANT_PRESERVING = "invariant_preserving"
    STATISTICALLY_BOUNDED = "statistically_bounded"


class EvidenceDeterminism(StrEnum):
    """Evidence determinism; wrong value breaks evidence trust."""

    DETERMINISTIC = "deterministic"
    SAMPLED = "sampled"
    EXTERNAL = "external"


class EntropySource(StrEnum):
    """Entropy sources; misuse breaks nondeterminism tracking."""

    SEEDED_RNG = "seeded_rng"
    EXTERNAL_ORACLE = "external_oracle"
    HUMAN_INPUT = "human_input"
    DATA = "data"


class NonDeterminismIntentSource(StrEnum):
    """Declared nondeterminism sources; misuse breaks intent contracts."""

    LLM = "llm"
    RETRIEVAL = "retrieval"
    HUMAN = "human"
    EXTERNAL = "external"


class EntropyMagnitude(StrEnum):
    """Entropy magnitude; wrong value breaks budget enforcement."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntropySeverity(StrEnum):
    """Entropy severity; wrong value breaks classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntropyExhaustionAction(StrEnum):
    """Entropy exhaustion action; wrong value breaks governance."""

    HALT = "halt"
    DEGRADE = "degrade"
    MARK_NON_CERTIFIABLE = "mark_non_certifiable"


class VerificationRandomness(StrEnum):
    """Verification randomness; wrong value breaks verification policy."""

    DETERMINISTIC = "deterministic"
    SAMPLED = "sampled"
    STATISTICAL = "statistical"


class ReasonCode(StrEnum):
    """Reason codes; misuse breaks failure classification."""

    CONTRADICTION_DETECTED = "contradiction_detected"


__all__ = [
    "Agent",
    "Tool",
    "Action",
    "Artifact",
    "Evidence",
    "Flow",
    "Step",
    "ArtifactType",
    "ArtifactScope",
    "CausalityTag",
    "EventType",
    "StepType",
    "VerificationPhase",
    "ArbitrationRule",
    "DeterminismLevel",
    "DeterminismClass",
    "ReplayMode",
    "FlowState",
    "DatasetState",
    "ReplayAcceptability",
    "EvidenceDeterminism",
    "EntropySource",
    "NonDeterminismIntentSource",
    "EntropyMagnitude",
    "EntropySeverity",
    "EntropyExhaustionAction",
    "ReasonCode",
    "VerificationRandomness",
]
