# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import pytest

from agentic_flows.spec.contracts.dataset_contract import validate_transition
from agentic_flows.spec.ontology import DatasetState

pytestmark = pytest.mark.unit


def test_dataset_state_transition_rejects_regression() -> None:
    with pytest.raises(ValueError, match="transition"):
        validate_transition(DatasetState.DEPRECATED, DatasetState.FROZEN)
