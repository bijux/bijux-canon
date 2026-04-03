# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.observability.capture.environment import (
    compute_environment_fingerprint,
)
from agentic_flows.runtime.orchestration.determinism_guard import validate_determinism
from agentic_flows.spec.ontology import DeterminismLevel

pytestmark = pytest.mark.regression


def test_unordered_normalization_is_required() -> None:
    with pytest.raises(ValueError, match="unordered collections must be normalized"):
        validate_determinism(
            environment_fingerprint=compute_environment_fingerprint(),
            seed="seed",
            unordered_normalized=False,
            determinism_level=DeterminismLevel.BOUNDED,
        )
