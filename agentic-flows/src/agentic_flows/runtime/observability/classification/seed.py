# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for runtime/observability/classification/seed.py."""

from __future__ import annotations

import hashlib


def deterministic_seed(step_index: int, inputs_fingerprint: str) -> int:
    """Execute deterministic_seed and enforce its contract."""
    payload = f"{step_index}:{inputs_fingerprint}".encode()
    digest = hashlib.sha256(payload).hexdigest()
    return int(digest[:8], 16)
