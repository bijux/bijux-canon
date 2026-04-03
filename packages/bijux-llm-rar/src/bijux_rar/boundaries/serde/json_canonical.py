# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from typing import Any

from bijux_rar.core.fingerprints import canonical_dumps


def canonical_json_line(obj: Any) -> str:
    """
    Canonical JSON line (no trailing spaces), always ends with newline when used by writers.
    """
    return canonical_dumps(obj)
