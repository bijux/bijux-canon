# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.contracts.artifact_contract import validate
from bijux_canon_runtime.spec.ontology import ArtifactType

pytestmark = pytest.mark.unit


def test_artifact_lineage_violation_raises() -> None:
    with pytest.raises(ValueError, match="must not declare parent artifact"):
        validate(
            parent_types=[ArtifactType.EXECUTION_TRACE],
            child_type=ArtifactType.FLOW_MANIFEST,
        )
