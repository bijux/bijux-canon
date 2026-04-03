"""Centralized semantic enums for Bijux Agent."""

from __future__ import annotations

from enum import Enum


class AgentType(str, Enum):
    """Named agents participating in the pipeline lifecycle."""

    READER = "reader"
    SUMMARIZER = "summarizer"
    CRITIQUE = "critique"
    TASKHANDLER = "taskhandler"
    PLANNER = "planner"
    JUDGE = "judge"
    VERIFIER = "verifier"
    ORCHESTRATOR = "orchestrator"


class AgentStatus(str, Enum):
    """States describing an agent's lifecycle during a run."""

    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    ABORTED = "aborted"


class DecisionOutcome(str, Enum):
    """Canonical verdicts emitted by pipeline agents."""

    APPROVE = "pass"
    PASS = APPROVE
    VETO = "veto"


class FailureMode(str, Enum):
    """Classifies the severity of agent/system failures."""

    TIMEOUT = "TIMEOUT"
    TRANSIENT = "TRANSIENT"
    VALIDATION_ERROR = "VALIDATION_ERROR"
    FATAL = "FATAL"


class ConfidenceLevel(str, Enum):
    """Buckets that map floating-point confidences to qualitative levels."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"

    @classmethod
    def for_confidence(cls, confidence: float) -> ConfidenceLevel:
        if confidence >= 0.85:
            return cls.HIGH
        if confidence >= 0.5:
            return cls.MEDIUM
        return cls.LOW


class ExecutionMode(str, Enum):
    """Executes tasks synchronously or asynchronously."""

    SYNC = "sync"
    ASYNC = "async"


class PipelineState(str, Enum):
    """Abstract lifecycle states for high-level orchestration."""

    INIT = "init"
    RUNNING = "running"
    JUDGING = "judging"
    VERIFIED = "verified"
    DONE = "done"
    ABORTED = "aborted"
