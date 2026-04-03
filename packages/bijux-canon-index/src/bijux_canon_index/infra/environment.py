# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import os


def read_env(
    primary: str,
    *,
    legacy: str | None = None,
    default: str | None = None,
) -> str | None:
    value = os.getenv(primary)
    if value not in (None, ""):
        return value
    if legacy is not None:
        legacy_value = os.getenv(legacy)
        if legacy_value not in (None, ""):
            return legacy_value
    return default


__all__ = ["read_env"]
