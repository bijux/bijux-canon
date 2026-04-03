# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.failures import FailureKind, classify_failure, retry_with_policy
from bijux_vex.core.errors import InvariantError, ValidationError, mark_retryable


def test_invariant_is_terminal():
    err = InvariantError(message="stop")
    assert classify_failure(err) is FailureKind.TERMINAL


def test_retry_policy_respects_retryable():
    err = ValidationError(message="retry me")
    retryable = mark_retryable(err)
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise retryable
        return "ok"

    assert retry_with_policy(flaky, attempts=3) == "ok"

    with pytest.raises(InvariantError):
        retry_with_policy(lambda: (_ for _ in ()).throw(InvariantError(message="bad")))


def test_retry_policy_obeys_contract():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        raise ValidationError(message="retry")

    with pytest.raises(ValidationError):
        retry_with_policy(flaky, attempts=3, contract=ExecutionContract.DETERMINISTIC)
    assert calls["n"] == 1
