# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import dataclasses
from decimal import Decimal

import pytest
from pydantic import BaseModel

from bijux_rar.core.fingerprints import canonical_dumps, fingerprint_obj, stable_id


class _Model(BaseModel):
    x: int
    y: str


@dataclasses.dataclass
class _DC:
    a: int
    b: list[int]


def test_canonical_dumps_is_sorted_and_locale_independent() -> None:
    obj = {"b": [3, 2, 1], "a": 1}
    s = canonical_dumps(obj)
    assert s == '{"a":1,"b":[3,2,1]}'


def test_canonical_dumps_dataclass_and_model() -> None:
    dc = _DC(a=1, b=[2, 3])
    mdl = _Model(x=1, y="z")
    assert canonical_dumps(dc) == '{"a":1,"b":[2,3]}'
    assert canonical_dumps(mdl) == '{"x":1,"y":"z"}'


def test_canonical_dumps_decimal_and_float() -> None:
    obj = {"pi": Decimal("3.14"), "f": 1.0}
    out = canonical_dumps(obj)
    assert out == '{"f":1.0,"pi":"3.14"}'


def test_canonical_dumps_rejects_non_string_keys() -> None:
    with pytest.raises(ValueError):
        canonical_dumps({1: "bad"})  # type: ignore[arg-type]


def test_stable_id_is_deterministic_and_versioned() -> None:
    obj = {"a": 1, "b": [2, 3]}
    sid1 = stable_id("kind", obj)
    sid2 = stable_id("kind", {"b": [2, 3], "a": 1})
    assert sid1 == sid2
    assert "_v1_" in sid1


def test_fingerprint_obj_matches_stable_id_suffix() -> None:
    obj = {"k": "v"}
    fp = fingerprint_obj(obj)
    sid = stable_id("t", obj)
    assert fp in sid
