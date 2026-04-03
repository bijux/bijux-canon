from __future__ import annotations

from typing import cast

import pytest

from bijux_agent.pipeline.control.phases import PipelinePhase
from bijux_agent.pipeline.results.failure import (
    FailureArtifact,
    FailureCategory,
    FailureClass,
    failure_profile_for,
    validate_failure_artifact,
)


def test_failure_profiles_cover_all_classes() -> None:
    for failure_class in cast(list[FailureClass], list(FailureClass)):
        profile = failure_profile_for(failure_class)
        assert isinstance(profile.retryable, bool)
        assert isinstance(profile.user_visible, bool)
        assert isinstance(profile.replayable, bool)


def test_failure_artifact_validation_enforces_category() -> None:
    artifact = FailureArtifact(
        failure_class=FailureClass.EPISTEMIC_UNCERTAINTY,
        mode="uncertain",
        message="epistemic failure",
        phase=PipelinePhase.ABORTED,
        recoverable=False,
        category=FailureCategory.EPISTEMIC,
    )
    validate_failure_artifact(artifact)


def test_failure_artifact_validation_rejects_mismatch() -> None:
    artifact = FailureArtifact(
        failure_class=FailureClass.EPISTEMIC_UNCERTAINTY,
        mode="uncertain",
        message="epistemic failure",
        phase=PipelinePhase.ABORTED,
        recoverable=False,
        category=FailureCategory.OPERATIONAL,
    )
    with pytest.raises(RuntimeError, match="category does not match"):
        validate_failure_artifact(artifact)
