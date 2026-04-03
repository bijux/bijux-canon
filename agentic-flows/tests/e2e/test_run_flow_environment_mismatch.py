# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.runtime.orchestration.determinism_guard import (
    validate_determinism,
)
from agentic_flows.spec.ontology import DeterminismLevel

pytestmark = pytest.mark.e2e


def test_environment_fingerprint_mismatch_is_blocking() -> None:
    with pytest.raises(ValueError, match="environment_fingerprint mismatch"):
        validate_determinism(
            environment_fingerprint="env-expected",
            seed="seed",
            unordered_normalized=True,
            determinism_level=DeterminismLevel.STRICT,
        )
