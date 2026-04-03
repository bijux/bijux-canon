# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import duckdb
import pytest

from agentic_flows.runtime.context import RunMode
from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from agentic_flows.spec.model.artifact.entropy_usage import EntropyUsage
from agentic_flows.spec.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from agentic_flows.spec.ontology import EntropyMagnitude
from agentic_flows.spec.ontology.public import EntropySource

pytestmark = pytest.mark.unit


def test_entropy_budget_rejects_disallowed_source(
    execution_store: DuckDBExecutionWriteStore, resolved_flow
) -> None:
    execution_store.register_dataset(resolved_flow.plan.dataset)
    run_id = execution_store.begin_run(plan=resolved_flow.plan, mode=RunMode.LIVE)
    execution_store.save_steps(
        run_id=run_id,
        tenant_id=resolved_flow.plan.tenant_id,
        plan=resolved_flow.plan,
    )
    usage = EntropyUsage(
        spec_version="v1",
        tenant_id=resolved_flow.plan.tenant_id,
        source=EntropySource.EXTERNAL_ORACLE,
        magnitude=EntropyMagnitude.LOW,
        description="external",
        step_index=0,
        nondeterminism_source=NonDeterminismSource(
            source=EntropySource.EXTERNAL_ORACLE,
            authorized=True,
            scope=resolved_flow.plan.flow_id,
        ),
    )
    with pytest.raises(duckdb.ConstraintException):
        execution_store.append_entropy_usage(
            run_id=run_id,
            usage=(usage,),
            starting_index=0,
        )


def test_entropy_budget_rejects_excess_magnitude(
    execution_store: DuckDBExecutionWriteStore, resolved_flow
) -> None:
    execution_store.register_dataset(resolved_flow.plan.dataset)
    run_id = execution_store.begin_run(plan=resolved_flow.plan, mode=RunMode.LIVE)
    execution_store.save_steps(
        run_id=run_id,
        tenant_id=resolved_flow.plan.tenant_id,
        plan=resolved_flow.plan,
    )
    usage = EntropyUsage(
        spec_version="v1",
        tenant_id=resolved_flow.plan.tenant_id,
        source=EntropySource.SEEDED_RNG,
        magnitude=EntropyMagnitude.HIGH,
        description="too_high",
        step_index=0,
        nondeterminism_source=NonDeterminismSource(
            source=EntropySource.SEEDED_RNG,
            authorized=True,
            scope=resolved_flow.plan.flow_id,
        ),
    )
    with pytest.raises(duckdb.ConstraintException):
        execution_store.append_entropy_usage(
            run_id=run_id,
            usage=(usage,),
            starting_index=0,
        )
