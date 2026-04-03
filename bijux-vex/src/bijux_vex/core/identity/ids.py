# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
"""
Versioned fingerprints and stable IDs built from canonical bytes.
"""

from __future__ import annotations

import hashlib
from typing import Any

from bijux_vex.core.canon import CANON_VERSION, canon


def fingerprint(
    obj: Any,
    *,
    canon_version: str = CANON_VERSION,
    algo: str = "sha256",
    salt: bytes | None = None,
) -> str:
    """Return a versioned fingerprint for an object."""
    data = canon(obj)
    hasher = hashlib.new(algo)
    hasher.update(canon_version.encode("utf-8"))
    if salt:
        hasher.update(b":salt:")
        hasher.update(salt)
    hasher.update(b":payload:")
    hasher.update(data)
    return hasher.hexdigest()


def make_id(
    prefix: str,
    obj: Any,
    *,
    canon_version: str = CANON_VERSION,
    algo: str = "sha256",
    salt: bytes | None = None,
) -> str:
    """Return a stable ID with prefix and canon version embedded."""
    fp = fingerprint(obj, canon_version=canon_version, algo=algo, salt=salt)
    return f"{prefix}:{canon_version}:{fp}"
