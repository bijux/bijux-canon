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


def test_strict_mode_requires_seed() -> None:
    with pytest.raises(ValueError, match="deterministic seed is required"):
        validate_determinism(
            environment_fingerprint=compute_environment_fingerprint(),
            seed=None,
            unordered_normalized=True,
            determinism_level=DeterminismLevel.STRICT,
        )
