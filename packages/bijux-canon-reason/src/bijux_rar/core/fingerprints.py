# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import dataclasses
from decimal import Decimal
import hashlib
import json
import math
from typing import Any

from pydantic import BaseModel

_JSON_PRIMITIVE = (str, int, bool, type(None))
CANONICAL_VERSION = 1
FINGERPRINT_ALGO = "sha256"
FINGERPRINT_SCHEMA_VERSION = 1
CANONICAL_VERSION = 1
FINGERPRINT_ALGO = "sha256"


def _normalize_float(x: float) -> float:
    if not math.isfinite(x):
        raise ValueError("Non-finite float is not allowed in canonical JSON.")
    if x == 0.0:
        return 0.0
    return x


def _normalize_decimal(x: Decimal) -> str:
    return format(x, "f")


def _to_canonical_obj(obj: Any) -> Any:
    if isinstance(obj, BaseModel):
        return _to_canonical_obj(obj.model_dump(mode="json"))
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return _to_canonical_obj(dataclasses.asdict(obj))

    if isinstance(obj, _JSON_PRIMITIVE):
        return obj

    if isinstance(obj, float):
        return _normalize_float(obj)

    if isinstance(obj, Decimal):
        return _normalize_decimal(obj)

    if isinstance(obj, (list, tuple)):
        return [_to_canonical_obj(x) for x in obj]

    if isinstance(obj, dict):
        out: dict[str, Any] = {}
        for k, v in obj.items():
            if not isinstance(k, str):
                raise ValueError(
                    f"Non-string dict key not allowed in canonical JSON: {type(k)}"
                )
            out[k] = _to_canonical_obj(v)
        return out

    raise ValueError(f"Unsupported type for canonicalization: {type(obj)}")


def canonical_dumps(obj: Any) -> str:
    canon = _to_canonical_obj(obj)
    return json.dumps(
        canon,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def fingerprint_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def fingerprint_obj(obj: Any) -> str:
    s = canonical_dumps(obj)
    return fingerprint_bytes(s.encode("utf-8"))


def stable_id(kind: str, obj: Any) -> str:
    fp = fingerprint_obj(obj)
    return f"{kind}_v{CANONICAL_VERSION}_{fp}"
