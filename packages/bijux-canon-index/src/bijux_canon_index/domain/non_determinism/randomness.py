# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi <bijan@bijux.io>
"""Randomness helpers for domain logic."""

from __future__ import annotations

from bijux_canon_index.core.contracts.execution_contract import ExecutionContract
from bijux_canon_index.core.errors import InvariantError
from bijux_canon_index.core.runtime.execution_session import ExecutionSession
from bijux_canon_index.core.runtime.vector_execution import RandomnessProfile
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner


def require_randomness_for_nd(
    session: ExecutionSession, ann_runner: AnnExecutionRequestRunner | None
) -> None:
    """Require randomness for ND."""
    if session.request.execution_contract is ExecutionContract.DETERMINISTIC:
        return
    if ann_runner is None:
        raise InvariantError(message="ND execution requires an ANN runner")
    if session.randomness is None:
        raise InvariantError(message="ND execution requires randomness profile")


def validate_randomness_profile(profile: RandomnessProfile | None) -> None:
    """Validate randomness profile."""
    if profile is None:
        raise InvariantError(message="ND randomness profile missing")
    if not profile.sources:
        raise InvariantError(message="ND randomness sources missing")


def enforce_randomness_contract(
    session: ExecutionSession,
    approximation_present: bool,
) -> None:
    """Enforce randomness contract."""
    if session.request.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
        return
    validate_randomness_profile(session.randomness)
    if not approximation_present:
        raise InvariantError(
            message="Non-deterministic execution missing approximation report"
        )


def validate_randomness_payload(payload: object) -> None:
    """Validate randomness payload."""
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
