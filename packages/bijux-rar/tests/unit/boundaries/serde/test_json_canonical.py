# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from bijux_rar.boundaries.serde.json_canonical import canonical_json_line


def test_canonical_json_bytes_is_deterministic() -> None:
    data1 = {"b": [2, 1], "a": 3}
    data2 = {"a": 3, "b": [2, 1]}
    c1 = canonical_json_line(data1)
    c2 = canonical_json_line(data2)
    assert c1 == c2
    # ordering must be stable
    assert c1.startswith("{\"a\"")
