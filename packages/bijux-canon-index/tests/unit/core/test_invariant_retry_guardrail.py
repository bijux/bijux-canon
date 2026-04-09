# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.core.errors import InvariantError, mark_retryable
from bijux_canon_index.core.failures import FailureKind, classify_failure


def test_invariant_retry_annotation_is_ignored():
    err = InvariantError(message="no-retry")
    retryable = mark_retryable(err)
    assert classify_failure(retryable) is FailureKind.TERMINAL
