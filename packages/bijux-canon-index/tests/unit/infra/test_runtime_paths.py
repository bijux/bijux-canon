# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from pathlib import Path

from bijux_canon_index.infra.runtime_paths import (
    default_embedding_cache_path,
    default_pgvector_state_path,
    default_state_path,
    ensure_parent_dir,
)


def test_default_runtime_paths_live_under_package_artifacts() -> None:
    assert default_state_path() == Path(
        "artifacts/03-bijux-canon-index/state/session.sqlite"
    )
    assert default_embedding_cache_path() == Path(
        "artifacts/03-bijux-canon-index/cache/embeddings.sqlite"
    )
    assert default_pgvector_state_path() == Path(
        "artifacts/03-bijux-canon-index/state/pgvector.sqlite"
    )


def test_ensure_parent_dir_creates_parent_directories(tmp_path: Path) -> None:
    target = tmp_path / "state" / "session.sqlite"
    resolved = ensure_parent_dir(target)
    assert resolved == target
    assert target.parent.is_dir()
