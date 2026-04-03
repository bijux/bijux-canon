# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.contracts.compatibility_contract import (
    allowed_to_evolve,
    breaks_determinism,
    breaks_replay,
)

pytestmark = pytest.mark.regression


def test_replay_breaker_detected() -> None:
    assert breaks_replay("plan_hash") is True


def test_replay_safe_change_allowed() -> None:
    assert breaks_replay("non_semantic_metadata") is False


def test_determinism_breaker_detected() -> None:
    assert breaks_determinism("environment_fingerprint") is True


def test_allowed_evolution_detected() -> None:
    assert allowed_to_evolve("doc_text") is True
