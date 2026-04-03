# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.runtime.observability.analysis.trace_diff import entropy_summary
from bijux_canon_runtime.model.artifact.entropy_usage import EntropyUsage
from bijux_canon_runtime.model.artifact.non_determinism_source import (
    NonDeterminismSource,
)
from bijux_canon_runtime.ontology import EntropyMagnitude
from bijux_canon_runtime.ontology.ids import FlowID, TenantID
from bijux_canon_runtime.ontology.public import EntropySource

pytestmark = pytest.mark.regression


def test_entropy_summary_reports_max_magnitude() -> None:
    usage = (
        EntropyUsage(
            spec_version="v1",
            tenant_id=TenantID("tenant-a"),
            source=EntropySource.SEEDED_RNG,
            magnitude=EntropyMagnitude.LOW,
            description="seeded",
            step_index=0,
            nondeterminism_source=NonDeterminismSource(
                source=EntropySource.SEEDED_RNG,
                authorized=True,
                scope=FlowID("flow-entropy"),
            ),
        ),
        EntropyUsage(
            spec_version="v1",
            tenant_id=TenantID("tenant-a"),
            source=EntropySource.DATA,
            magnitude=EntropyMagnitude.HIGH,
            description="data",
            step_index=1,
            nondeterminism_source=NonDeterminismSource(
                source=EntropySource.DATA,
                authorized=True,
                scope=FlowID("flow-entropy"),
            ),
        ),
    )

    summary = entropy_summary(usage)
    assert summary["sources"] == ["data", "seeded_rng"]
    assert summary["max_magnitude"] == EntropyMagnitude.HIGH.value
