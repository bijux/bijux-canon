# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import json
from pathlib import Path
import sys

import pytest

PACKAGE_ROOT = Path(__file__).resolve().parents[1]
SRC_ROOT = PACKAGE_ROOT / "src"

if str(SRC_ROOT) not in sys.path:
    sys.path.insert(0, str(SRC_ROOT))


@pytest.fixture
def snapshot() -> object:
    """Very small file-backed snapshot for deterministic schema outputs (Bijux RAG)."""

    snap_path = Path(__file__).parent / "_snapshots" / "chunk_model_schema.json"
    if not snap_path.exists():
        raise FileNotFoundError(
            f"Missing snapshot file {snap_path}. Regenerate it by running "
            '`python -c "from bijux_canon_ingest.interfaces.serialization.pydantic_models import ChunkModel; '
            'import json; print(json.dumps(ChunkModel.model_json_schema(), sort_keys=True))"` '
            "and saving the output to that path."
        )
    return json.loads(snap_path.read_text(encoding="utf-8"))
