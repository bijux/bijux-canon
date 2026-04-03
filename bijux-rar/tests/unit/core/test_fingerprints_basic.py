# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_rar.core.fingerprints import (
    canonical_dumps,
    fingerprint_bytes,
    fingerprint_obj,
)


def test_canonical_json_orders_keys() -> None:
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert canonical_dumps(a) == canonical_dumps(b)


def test_fingerprint_is_order_invariant_for_dict_keys() -> None:
    a = {"b": 1, "a": 2}
    b = {"a": 2, "b": 1}
    assert fingerprint_obj(a) == fingerprint_obj(b)


def test_canonical_rejects_non_string_keys() -> None:
    with pytest.raises(ValueError, match="Non-string dict key"):
        canonical_dumps({1: "x"})


def test_canonical_rejects_non_finite_float() -> None:
    with pytest.raises(ValueError, match="Non-finite float"):
        canonical_dumps({"x": float("nan")})


def test_fingerprint_bytes_uses_sha256() -> None:
    digest = fingerprint_bytes(b"abc")
    assert digest.startswith("ba7816bf")
