# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/classification/fingerprint.py."""

from __future__ import annotations

from dataclasses import asdict, is_dataclass
import hashlib
import json
from typing import Any


def _normalize(value: Any) -> Any:
    """Internal helper; not part of the public API."""
    if isinstance(value, dict):
        return {key: _normalize(value[key]) for key in sorted(value)}
    if isinstance(value, list | tuple | set):
        normalized = [_normalize(item) for item in value]
        return sorted(
            normalized,
            key=lambda item: json.dumps(item, sort_keys=True, separators=(",", ":")),
        )
    return value


def fingerprint_inputs(data: dict) -> str:
    """Execute fingerprint_inputs and enforce its contract."""
    normalized = _normalize(data)
    payload = json.dumps(
        normalized, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    )
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def fingerprint_policy(policy: object) -> str:
    """Execute fingerprint_policy and enforce its contract."""
    payload = asdict(policy) if is_dataclass(policy) else {"policy": str(policy)}
    return fingerprint_inputs(payload)
