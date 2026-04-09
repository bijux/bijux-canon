# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared helpers for retrieval index implementations."""

from __future__ import annotations

from hashlib import sha256
import json

import numpy as np
from numpy.typing import NDArray
from typing import cast

SCHEMA_VERSION = 1


def fingerprint_bytes(*parts: bytes) -> str:
    digest = sha256()
    for part in parts:
        digest.update(part)
    return digest.hexdigest()


def canonical_json_dumps(obj: object) -> bytes:
    return json.dumps(
        obj,
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")


def l2_normalize(x: NDArray[np.float32]) -> NDArray[np.float32]:
    denom = np.linalg.norm(x, axis=1, keepdims=True)
    denom = np.maximum(denom, np.float32(1e-12))
    return cast(NDArray[np.float32], x / denom)


__all__ = [
    "SCHEMA_VERSION",
    "canonical_json_dumps",
    "fingerprint_bytes",
    "l2_normalize",
]
