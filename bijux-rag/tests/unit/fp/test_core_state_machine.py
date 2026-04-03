# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from hypothesis import given
from hypothesis import strategies as st

from bijux_rag.fp.core import (
    Done,
    ErrorCode,
    EvAdvance,
    Failed,
    advance_event,
    done,
    fail_event,
    failed,
    pending,
    running,
    start_event,
    succeed_event,
    transition,
)

UTC = timezone.utc
aware_dt = st.datetimes(timezones=st.just(UTC))


@given(queued_at=aware_dt)
def test_pending_naive_rejected(queued_at: datetime) -> None:
    naive = queued_at.replace(tzinfo=None)
    with pytest.raises(ValueError):
        pending(queued_at=naive)


@given(delta=st.integers(max_value=-1))
def test_advance_negative_rejected(delta: int) -> None:
    with pytest.raises(ValueError):
        advance_event(delta_permille=delta)


@given(
    started_at=aware_dt,
    progress=st.integers(min_value=0, max_value=1000),
    delta=st.integers(min_value=0, max_value=2000),
)
def test_progress_monotonic_and_clamped(started_at: datetime, progress: int, delta: int) -> None:
    state = running(started_at=started_at, progress_permille=progress)
    ev = advance_event(delta_permille=delta)
    new_state = transition(state, ev)
    assert new_state.progress_permille >= state.progress_permille
    assert new_state.progress_permille <= 1000


@given(
    state=st.one_of(
        st.builds(
            done,
            completed_at=aware_dt,
            artifact_id=st.text(min_size=1),
            dim=st.integers(min_value=1, max_value=8192),
            sha256=st.just("0" * 64),
        ),
        st.builds(
            failed,
            failed_at=aware_dt,
            code=st.sampled_from(list(ErrorCode)),
            msg=st.text(),
            attempt=st.integers(min_value=1, max_value=10),
        ),
    )
)
def test_terminal_idempotent(state: Done | Failed) -> None:
    for ev in [
        start_event(started_at=datetime.now(UTC)),
        advance_event(delta_permille=100),
        succeed_event(completed_at=datetime.now(UTC), artifact_id="x", dim=1, sha256="0" * 64),
        fail_event(failed_at=datetime.now(UTC), code=ErrorCode.INTERNAL, msg="", attempt=1),
    ]:
        assert transition(state, ev) == state


def test_transition_invalid_raises_with_context() -> None:
    s = pending(queued_at=datetime.now(UTC))
    with pytest.raises(ValueError):
        transition(s, EvAdvance(delta_permille=1))
