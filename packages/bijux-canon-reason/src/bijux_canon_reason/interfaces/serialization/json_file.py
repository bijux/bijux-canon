# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""JSON file helpers."""

from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from bijux_canon_reason.core.fingerprints import canonical_dumps


def _atomic_write_bytes(path: Path, data: bytes) -> None:
    """Handle atomic write bytes."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        dir=path.parent, prefix=path.name, suffix=".tmp", delete=False
    ) as tmp:
        tmp.write(data)
        tmp.flush()
        os.fsync(tmp.fileno())
        tmp_path = Path(tmp.name)
    tmp_path.replace(path)


def write_json_file(path: Path, obj: Any) -> None:
    """Write JSON file."""
    payload = (canonical_dumps(obj) + "\n").encode("utf-8")
    _atomic_write_bytes(path, payload)


def read_json_file(path: Path) -> Any:
    """Read JSON file."""
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "canonical_version" in data and "data" in data:
        return data["data"]
    return data
