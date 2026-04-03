# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.core.canon import CANON_VERSION, canon
from bijux_vex.core.identity.ids import fingerprint


def test_canon_version_constant_default():
    assert CANON_VERSION == "v1"


def test_fingerprint_changes_with_version():
    obj = {"a": 1, "b": [2, 3]}
    base = fingerprint(obj)
    bumped = fingerprint(obj, canon_version="v2")
    assert base != bumped
    assert canon(obj) == canon(obj)  # stability guard
