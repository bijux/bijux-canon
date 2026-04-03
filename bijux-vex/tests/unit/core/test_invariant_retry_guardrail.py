# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.failures import classify_failure, FailureKind
from bijux_vex.core.errors import InvariantError, mark_retryable


def test_invariant_retry_annotation_is_ignored():
    err = InvariantError(message="no-retry")
    retryable = mark_retryable(err)
    assert classify_failure(retryable) is FailureKind.TERMINAL
