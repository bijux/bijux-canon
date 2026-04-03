# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

import json
import os
from pathlib import Path
import tempfile
from typing import Any

from bijux_rar.core.fingerprints import canonical_dumps


def _atomic_write_bytes(path: Path, data: bytes) -> None:
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
    payload = (canonical_dumps(obj) + "\n").encode("utf-8")
    _atomic_write_bytes(path, payload)


def read_json_file(path: Path) -> Any:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict) and "canonical_version" in data and "data" in data:
        return data["data"]
    return data
