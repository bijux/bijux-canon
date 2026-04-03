# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.determinism import classify_execution
from bijux_vex.core.runtime.execution_session import ExecutionSession
from bijux_vex.domain.nd.randomness import require_randomness_for_nd
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


def require_randomness(
    session: ExecutionSession, ann_runner: AnnExecutionRequestRunner | None
) -> None:
    classify_execution(
        contract=session.request.execution_contract,
        randomness=session.randomness,
        ann_runner=ann_runner,
        vector_store=None,
    )
    require_randomness_for_nd(session, ann_runner)
