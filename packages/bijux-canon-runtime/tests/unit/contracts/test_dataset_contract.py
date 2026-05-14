# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_runtime.contracts.dataset_contract import validate_transition
from bijux_canon_runtime.ontology import DatasetState

pytestmark = pytest.mark.unit


def test_dataset_state_transition_rejects_regression() -> None:
    with pytest.raises(ValueError, match="transition"):
        validate_transition(DatasetState.DEPRECATED, DatasetState.FROZEN)
