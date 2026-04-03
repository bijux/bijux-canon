# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""Shared pytest fixtures for the test suite."""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def snapshot() -> object:
    """Very small file-backed snapshot for deterministic schema outputs (Bijux RAG)."""

    snap_path = Path(__file__).parent / "_snapshots" / "chunk_model_schema.json"
    if not snap_path.exists():
        raise FileNotFoundError(
            f"Missing snapshot file {snap_path}. Regenerate it by running "
            '`python -c "from bijux_rag.boundaries.adapters.pydantic_edges import ChunkModel; '
            'import json; print(json.dumps(ChunkModel.model_json_schema(), sort_keys=True))"` '
            "and saving the output to that path."
        )
    return json.loads(snap_path.read_text(encoding="utf-8"))
