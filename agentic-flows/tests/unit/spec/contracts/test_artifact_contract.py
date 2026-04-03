# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.contracts.artifact_contract import validate
from agentic_flows.spec.ontology import ArtifactType

pytestmark = pytest.mark.unit


def test_artifact_lineage_violation_raises() -> None:
    with pytest.raises(ValueError, match="must not declare parent artifact"):
        validate(
            parent_types=[ArtifactType.EXECUTION_TRACE],
            child_type=ArtifactType.FLOW_MANIFEST,
        )
