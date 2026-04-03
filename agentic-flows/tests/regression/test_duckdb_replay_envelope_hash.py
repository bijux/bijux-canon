# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import asdict

import pytest

from agentic_flows.runtime.observability.classification.fingerprint import (
    fingerprint_inputs,
)
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)

pytestmark = pytest.mark.regression


def test_duckdb_replay_envelope_hash_is_stable(
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

    stored = execution_read_store.load_replay_envelope(
        result.run_id, tenant_id=result.trace.tenant_id
    )
    expected = fingerprint_inputs(asdict(resolved_flow.plan.replay_envelope))
    stored_hash = fingerprint_inputs(asdict(stored))
    assert stored_hash == expected
