# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import duckdb
import pytest

from agentic_flows.runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor

pytestmark = pytest.mark.unit


def test_dataset_transition_rejected_by_db(
    execution_store: DuckDBExecutionWriteStore,
    dataset_descriptor: DatasetDescriptor,
) -> None:
    execution_store.register_dataset(dataset_descriptor)
    connection = execution_store._connection
    previous_state = connection.execute(
        """
        SELECT state FROM datasets
        WHERE tenant_id = ? AND dataset_id = ? AND version = ?
        """,
        (
            str(dataset_descriptor.tenant_id),
            str(dataset_descriptor.dataset_id),
            dataset_descriptor.dataset_version,
        ),
    ).fetchone()[0]
    with pytest.raises(duckdb.ConstraintException):
        connection.execute(
            """
            UPDATE datasets
            SET state = ?, previous_state = ?
            WHERE tenant_id = ? AND dataset_id = ? AND version = ?
            """,
            (
                "experimental",
                previous_state,
                str(dataset_descriptor.tenant_id),
                str(dataset_descriptor.dataset_id),
                dataset_descriptor.dataset_version,
            ),
        )
