# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Validation helpers for domain logic."""

from __future__ import annotations

from bijux_canon_index.core.determinism import classify_execution
from bijux_canon_index.core.runtime.execution_session import ExecutionSession
from bijux_canon_index.domain.non_determinism.randomness import (
    require_randomness_for_nd,
)
from bijux_canon_index.infra.adapters.ann_base import AnnExecutionRequestRunner


def require_randomness(
    session: ExecutionSession, ann_runner: AnnExecutionRequestRunner | None
) -> None:
    """Require randomness."""
    classify_execution(
        contract=session.request.execution_contract,
        randomness=session.randomness,
        ann_runner=ann_runner,
        vector_store=None,
    )
    require_randomness_for_nd(session, ann_runner)
