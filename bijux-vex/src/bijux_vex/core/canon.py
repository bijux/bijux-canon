# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Canonicalization utilities.

The goal is byte-identical output for identical inputs:
- sorted object keys
- stable list ordering (caller responsibility to provide deterministic order)
- finite floats only
"""

from __future__ import annotations

import base64
from collections.abc import Mapping
from dataclasses import asdict, is_dataclass
from enum import Enum
import json
import math
from typing import Any

CANON_VERSION = "v1"


def _normalize(obj: Any) -> Any:
    if is_dataclass(obj):
        return _normalize(asdict(obj))  # type: ignore[arg-type]
    if isinstance(obj, Mapping):
        return {str(k): _normalize(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize(v) for v in obj]
    if isinstance(obj, (bytes, bytearray)):
        try:
            return obj.decode("utf-8")
        except Exception:
            return base64.b64encode(bytes(obj)).decode("ascii")
    if isinstance(obj, Enum):
        return obj.value
    if obj is None or isinstance(obj, (str, bool, int)):
        return obj
    if isinstance(obj, float):
        if not math.isfinite(obj):
            raise ValueError("Non-finite floats are forbidden")
        return obj
    raise TypeError(f"Unsupported type for canonicalization: {type(obj)}")


def canon(obj: Any) -> bytes:
    """Return canonical bytes for an object according to determinism rules."""
    normalized = _normalize(obj)
    payload = json.dumps(
        normalized,
        sort_keys=True,
        ensure_ascii=True,
        separators=(",", ":"),
    )
    return payload.encode("utf-8")
