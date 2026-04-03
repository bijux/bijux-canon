"""Models to describe pipeline failures in structured form."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from pydantic import ConfigDict, Field

from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.schema.base import TypedBaseModel
from bijux_agent.utilities.final import final_class


class FailureCategory(str, Enum):
    EPISTEMIC = "epistemic_failure"
    OPERATIONAL = "operational_failure"


class FailureClass(str, Enum):
    USER_INTERRUPTION = "user_interruption"
    EPISTEMIC_UNCERTAINTY = "epistemic_uncertainty"
    VERIFICATION_VETO = "verification_veto"
    BUDGET_EXCEEDED = "budget_exceeded"
    MAX_ITERATIONS = "max_iterations"
    FATAL_FAILURE = "fatal_failure"
    EXECUTION_ERROR = "execution_error"
    VALIDATION_ERROR = "validation_error"
    RESOURCE_EXHAUSTION = "resource_exhaustion"


@final_class
class FailureArtifact(TypedBaseModel):
    model_config = ConfigDict(frozen=True, extra="forbid")
    """Structured payload describing why a pipeline failed."""

    failure_class: FailureClass = Field(
        ...,
        description="Machine-actionable failure classification",
    )
    mode: str = Field(..., description="Mode describing how failure was detected")
    message: str = Field(..., description="Human-readable failure message")
    phase: PipelinePhase = Field(
        ..., description="Canonical phase where failure occurred"
    )
    recoverable: bool = Field(
        False,
        description="Signals whether the runner should attempt recovery",
    )
    category: FailureCategory = Field(
        FailureCategory.OPERATIONAL,
        description="Class of failure guiding how to react",
    )


@dataclass(frozen=True)
class FailureProfile:
    retryable: bool
    user_visible: bool
    replayable: bool
    category: FailureCategory


FAILURE_PROFILES: dict[FailureClass, FailureProfile] = {
    FailureClass.USER_INTERRUPTION: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.EPISTEMIC_UNCERTAINTY: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.EPISTEMIC,
    ),
    FailureClass.VERIFICATION_VETO: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.BUDGET_EXCEEDED: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.MAX_ITERATIONS: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.FATAL_FAILURE: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=False,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.EXECUTION_ERROR: FailureProfile(
        retryable=True,
        user_visible=True,
        replayable=False,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.VALIDATION_ERROR: FailureProfile(
        retryable=False,
        user_visible=True,
        replayable=True,
        category=FailureCategory.OPERATIONAL,
    ),
    FailureClass.RESOURCE_EXHAUSTION: FailureProfile(
        retryable=True,
        user_visible=True,
        replayable=False,
        category=FailureCategory.OPERATIONAL,
    ),
}


def failure_profile_for(failure_class: FailureClass) -> FailureProfile:
    profile = FAILURE_PROFILES.get(failure_class)
    if profile is None:
        raise RuntimeError(f"Missing failure profile for {failure_class.value}")
    return profile


def validate_failure_artifact(artifact: FailureArtifact) -> FailureProfile:
    profile = failure_profile_for(artifact.failure_class)
    if artifact.category != profile.category:
        raise RuntimeError(
            "Failure artifact category does not match failure taxonomy profile"
        )
    if artifact.recoverable and not profile.retryable:
        raise RuntimeError(
            "Failure artifact marked recoverable but class is not retryable"
        )
    return profile


if set(FAILURE_PROFILES.keys()) != set(FailureClass):
    missing = set(FailureClass) - set(FAILURE_PROFILES.keys())
    extra = set(FAILURE_PROFILES.keys()) - set(FailureClass)
    raise RuntimeError(
        "Failure profiles must cover all failure classes: "
        f"missing={sorted(cls.value for cls in missing)} "
        f"extra={sorted(cls.value for cls in extra)}"
    )
