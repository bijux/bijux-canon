# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import replace

import pytest

from agentic_flows.runtime.orchestration.determinism_guard import validate_replay
from agentic_flows.runtime.orchestration.execute_flow import (
    ExecutionConfig,
    RunMode,
    execute_flow,
)
from agentic_flows.spec.model.verification.arbitration_policy import ArbitrationPolicy
from agentic_flows.spec.ontology import ArbitrationRule

pytestmark = pytest.mark.regression


def test_replay_rejects_policy_mismatch(
    resolved_flow, baseline_policy, execution_store
) -> None:
    result = execute_flow(
        resolved_flow=resolved_flow,
        config=ExecutionConfig(
            mode=RunMode.LIVE,
            determinism_level=resolved_flow.manifest.determinism_level,
            verification_policy=baseline_policy,
            execution_store=execution_store,
        ),
    )
    trace = result.trace
    plan = result.resolved_flow.plan

    changed_policy = replace(
        baseline_policy,
        arbitration_policy=ArbitrationPolicy(
            spec_version="v1",
            rule=ArbitrationRule.STRICT_FIRST_FAILURE,
            quorum_threshold=None,
        ),
    )

    with pytest.raises(ValueError, match="verification_policy"):
        validate_replay(trace, plan, verification_policy=changed_policy)
