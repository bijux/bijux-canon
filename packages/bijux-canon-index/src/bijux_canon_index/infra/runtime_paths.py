# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path


def package_artifacts_root() -> Path:
    return Path("artifacts") / "bijux-canon-index"


def default_state_path() -> Path:
    return package_artifacts_root() / "state" / "session.sqlite"


def default_embedding_cache_path() -> Path:
    return package_artifacts_root() / "cache" / "embeddings.sqlite"


def default_pgvector_state_path() -> Path:
    return package_artifacts_root() / "state" / "pgvector.sqlite"


def ensure_parent_dir(path: str | Path) -> Path:
    resolved = Path(path)
    resolved.parent.mkdir(parents=True, exist_ok=True)
    return resolved


__all__ = [
    "default_embedding_cache_path",
    "default_pgvector_state_path",
    "default_state_path",
    "ensure_parent_dir",
    "package_artifacts_root",
]
