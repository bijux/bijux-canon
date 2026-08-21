# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Explicit command-line acquisition of supported offline embedding models."""

from __future__ import annotations

import argparse
import importlib.metadata
import json
import platform
from collections.abc import Sequence
from pathlib import Path

from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE, EmbeddingProfile
from bijux_canon_index.infra.embeddings.model_cache import materialize_model

_PROFILES: dict[str, EmbeddingProfile] = {
    LOCAL_MINILM_PROFILE.profile_id: LOCAL_MINILM_PROFILE,
}


def _library_versions() -> tuple[tuple[str, str], ...]:
    names = ("bijux-canon-index", "numpy", "sentence-transformers", "torch")
    versions = [(name, importlib.metadata.version(name)) for name in names]
    versions.append(("python", platform.python_version()))
    return tuple(sorted(versions))


def materialize_profile(profile_id: str, cache_root: Path) -> dict[str, object]:
    """Acquire one named profile and return its complete canonical lock."""

    try:
        profile = _PROFILES[profile_id]
    except KeyError as error:
        supported = ", ".join(sorted(_PROFILES))
        raise ValueError(
            f"unsupported embedding profile {profile_id!r}; supported: {supported}"
        ) from error
    lock = materialize_model(
        profile,
        cache_root,
        library_versions=_library_versions(),
    )
    return lock.manifest()


def main(argv: Sequence[str] | None = None) -> int:
    """Run explicit network-backed model acquisition."""

    parser = argparse.ArgumentParser(
        description="Materialize a pinned bijux-canon embedding model for offline use."
    )
    parser.add_argument("--profile", choices=sorted(_PROFILES), required=True)
    parser.add_argument("--cache-root", type=Path, required=True)
    arguments = parser.parse_args(argv)
    manifest = materialize_profile(arguments.profile, arguments.cache_root)
    print(
        json.dumps(
            manifest,
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())


__all__ = ["main", "materialize_profile"]
