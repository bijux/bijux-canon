"""Ontology enums are frozen in v1; adding values requires a MAJOR bump, and reordering is forbidden."""
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from enum import Enum, auto

from agentic_flows.spec.ontology.ids import ActionID as Action
from agentic_flows.spec.ontology.ids import AgentID as Agent
from agentic_flows.spec.ontology.ids import ArtifactID as Artifact
from agentic_flows.spec.ontology.ids import EvidenceID as Evidence
from agentic_flows.spec.ontology.ids import FlowID as Flow
from agentic_flows.spec.ontology.ids import StepID as Step
from agentic_flows.spec.ontology.ids import ToolID as Tool


class ArtifactType(str, Enum):
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


class ArtifactScope(str, Enum):
    """Artifact scope boundary; mis-scoping breaks isolation."""

    EPHEMERAL = "ephemeral"
    WORKING = "working"
    AUDIT = "audit"


class EventType(str, Enum):
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


class CausalityTag(str, Enum):
    """Causality source tags; misuse breaks audit provenance."""

    AGENT = "agent"
    TOOL = "tool"
    DATASET = "dataset"
    ENVIRONMENT = "environment"
    HUMAN = "human"


class StepType(str, Enum):
    """Step types; misuse breaks step execution semantics."""

    AGENT = "agent"
    RETRIEVAL = "retrieval"
    REASONING = "reasoning"
    VERIFICATION = "verification"


class VerificationPhase(str, Enum):
    """Verification phases; misuse breaks gate ordering."""

    PRE_EXECUTION = "pre_execution"
    POST_EXECUTION = "post_execution"


class ArbitrationRule(str, Enum):
    """Arbitration rules; misuse breaks verification decisions."""

    UNANIMOUS = "unanimous"
    QUORUM = "quorum"
    STRICT_FIRST_FAILURE = "strict_first_failure"


class DeterminismLevel(str, Enum):
    """Determinism level; wrong value breaks enforcement."""

    STRICT = "strict"
    BOUNDED = "bounded"
    PROBABILISTIC = "probabilistic"
    UNCONSTRAINED = "unconstrained"


class DeterminismClass(str, Enum):
    """Determinism class; wrong value breaks classification."""

    STRUCTURAL = "structural"
    ENVIRONMENTAL = "environmental"
    STOCHASTIC = "stochastic"
    HUMAN = "human"
    EXTERNAL = "external"


class ReplayMode(str, Enum):
    """Replay modes; wrong value breaks replay governance."""

    STRICT = "strict"
    BOUNDED = "bounded"
    OBSERVATIONAL = "observational"


class FlowState(str, Enum):
    """Flow lifecycle state; misuse breaks flow governance."""

    DRAFT = "draft"
    VALIDATED = "validated"
    FROZEN = "frozen"
    DEPRECATED = "deprecated"


class DatasetState(str, Enum):
    """Dataset lifecycle state; misuse breaks dataset governance."""

    EXPERIMENTAL = "experimental"
    FROZEN = "frozen"
    DEPRECATED = "deprecated"


class ReplayAcceptability(str, Enum):
    """Replay acceptability; wrong value breaks replay contract."""

    EXACT_MATCH = "exact_match"
    INVARIANT_PRESERVING = "invariant_preserving"
    STATISTICALLY_BOUNDED = "statistically_bounded"


class EvidenceDeterminism(str, Enum):
    """Evidence determinism; wrong value breaks evidence trust."""

    DETERMINISTIC = "deterministic"
    SAMPLED = "sampled"
    EXTERNAL = "external"


class EntropySource(str, Enum):
    """Entropy sources; misuse breaks nondeterminism tracking."""

    SEEDED_RNG = "seeded_rng"
    EXTERNAL_ORACLE = "external_oracle"
    HUMAN_INPUT = "human_input"
    DATA = "data"


class NonDeterminismIntentSource(str, Enum):
    """Declared nondeterminism sources; misuse breaks intent contracts."""

    LLM = "llm"
    RETRIEVAL = "retrieval"
    HUMAN = "human"
    EXTERNAL = "external"


class EntropyMagnitude(str, Enum):
    """Entropy magnitude; wrong value breaks budget enforcement."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntropySeverity(str, Enum):
    """Entropy severity; wrong value breaks classification."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class EntropyExhaustionAction(str, Enum):
    """Entropy exhaustion action; wrong value breaks governance."""

    HALT = "halt"
    DEGRADE = "degrade"
    MARK_NON_CERTIFIABLE = "mark_non_certifiable"


class VerificationRandomness(str, Enum):
    """Verification randomness; wrong value breaks verification policy."""

    DETERMINISTIC = "deterministic"
    SAMPLED = "sampled"
    STATISTICAL = "statistical"


class ReasonCode(str, Enum):
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
