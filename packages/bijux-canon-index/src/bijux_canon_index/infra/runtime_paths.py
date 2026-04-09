# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Runtime paths helpers."""

from __future__ import annotations

from pathlib import Path


def package_artifacts_root() -> Path:
    """Handle package artifacts root."""
    return Path("artifacts") / "bijux-canon-index"


def default_state_path() -> Path:
    """Return the default state path."""
    return package_artifacts_root() / "state" / "session.sqlite"


def default_embedding_cache_path() -> Path:
    """Return the default embedding cache path."""
    return package_artifacts_root() / "cache" / "embeddings.sqlite"


def default_pgvector_state_path() -> Path:
    """Return the default pgvector state path."""
    return package_artifacts_root() / "state" / "pgvector.sqlite"


def ensure_parent_dir(path: str | Path) -> Path:
    """Ensure parent dir."""
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
