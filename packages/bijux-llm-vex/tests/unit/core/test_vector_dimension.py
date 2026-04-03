# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import Vector


def test_vector_dimension_must_match_values():
    with pytest.raises(InvariantError):
        Vector(
            vector_id="v1",
            chunk_id="c1",
            values=(0.0, 1.0, 2.0),
            dimension=2,
        )


def test_vector_dimension_positive():
    with pytest.raises(InvariantError):
        Vector(
            vector_id="v1",
            chunk_id="c1",
            values=(0.0,),
            dimension=0,
        )
