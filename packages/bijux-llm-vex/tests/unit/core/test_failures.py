# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.failures import FailureKind, classify_failure, retry_with_policy
from bijux_vex.core.errors import InvariantError, mark_retryable


def test_classify_and_retry():
    err = InvariantError(message="boom")
    assert classify_failure(err) is FailureKind.TERMINAL

    retryable = mark_retryable(err)
    assert classify_failure(retryable) is FailureKind.TERMINAL

    calls = {"count": 0}

    def sometimes():
        calls["count"] += 1
        if calls["count"] < 2:
            raise retryable
        return "ok"

    with pytest.raises(InvariantError):
        retry_with_policy(sometimes, attempts=3)

    def always_fail():
        raise err

    with pytest.raises(InvariantError):
        retry_with_policy(always_fail, attempts=1)
