# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.runtime.execution_session import ExecutionSession
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


def require_randomness_for_nd(
    session: ExecutionSession, ann_runner: AnnExecutionRequestRunner | None
) -> None:
    if session.request.execution_contract is ExecutionContract.DETERMINISTIC:
        return
    if ann_runner is None:
        raise InvariantError(message="ND execution requires an ANN runner")
    if session.randomness is None:
        raise InvariantError(message="ND execution requires randomness profile")


def validate_randomness_profile(profile: RandomnessProfile | None) -> None:
    if profile is None:
        raise InvariantError(message="ND randomness profile missing")
    if not profile.sources:
        raise InvariantError(message="ND randomness sources missing")


def enforce_randomness_contract(
    session: ExecutionSession,
    approximation_present: bool,
) -> None:
    if session.request.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
        return
    validate_randomness_profile(session.randomness)
    if not approximation_present:
        raise InvariantError(
            message="Non-deterministic execution missing approximation report"
        )


def validate_randomness_payload(payload: object) -> None:
    randomness_profile = getattr(payload, "randomness_profile", None)
    if randomness_profile is None:
        raise ValueError("randomness_profile required for non_deterministic execution")
    if getattr(randomness_profile, "seed", None) is None:
        sources = tuple(getattr(randomness_profile, "sources", None) or ())
        non_replayable = getattr(randomness_profile, "non_replayable", False)
        if not sources or not non_replayable:
            raise ValueError(
                "randomness_profile requires seed or non_replayable with explicit sources"
            )
