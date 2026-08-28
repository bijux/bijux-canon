# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Explicit command-line acquisition of supported offline embedding models."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
import json
from pathlib import Path

from bijux_canon_index.application.model_lifecycle import (
    acquire_model,
    supported_model_profile,
)
from bijux_canon_index.domain.embedding import LOCAL_MINILM_PROFILE

_PROFILES = (LOCAL_MINILM_PROFILE.profile_id,)


def materialize_profile(profile_id: str, cache_root: Path) -> dict[str, object]:
    """Acquire one named profile and return its complete canonical lock."""

    supported_model_profile(profile_id)
    return acquire_model(cache_root, profile_id=profile_id).record()


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
