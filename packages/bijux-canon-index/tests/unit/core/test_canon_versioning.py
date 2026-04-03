# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations
from bijux_canon_index.core.canon import CANON_VERSION, canon
from bijux_canon_index.core.identity.ids import fingerprint


def test_canon_version_constant_default():
    assert CANON_VERSION == "v1"


def test_fingerprint_changes_with_version():
    obj = {"a": 1, "b": [2, 3]}
    base = fingerprint(obj)
    bumped = fingerprint(obj, canon_version="v2")
    assert base != bumped
    assert canon(obj) == canon(obj)  # stability guard
