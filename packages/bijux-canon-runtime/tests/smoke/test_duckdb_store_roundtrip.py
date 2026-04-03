# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.runtime.orchestration.replay_store import replay_with_store

pytestmark = pytest.mark.smoke


def test_duckdb_store_roundtrip(
    resolved_flow, execution_store, execution_read_store
) -> None:
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    diff, _ = replay_with_store(
        store=execution_read_store,
        run_id=result.run_id,
        tenant_id=resolved_flow.manifest.tenant_id,
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.DRY_RUN,
            determinism_level=resolved_flow.manifest.determinism_level,
            execution_store=execution_store,
        ),
    )
    assert diff == {}
