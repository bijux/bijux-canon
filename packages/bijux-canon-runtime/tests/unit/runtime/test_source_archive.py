# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib

import pytest

from bijux_canon_ingest.application.canonical_ingest import CanonicalRetainedSource
from bijux_canon_runtime.runtime.persistence.source_archive import (
    SourceArchiveError,
    build_source_archive,
    read_source_archive,
)


def _source(path: str, content: bytes) -> CanonicalRetainedSource:
    return CanonicalRetainedSource(
        relative_path=path,
        media_type="text/plain",
        content_sha256=hashlib.sha256(content).hexdigest(),
        content=content,
    )


def test_source_archive_is_deterministic_and_resolves_exact_bytes() -> None:
    sources = (
        _source("nested/b.txt", b"second\n"),
        _source("a.txt", b"first\n"),
    )

    first = build_source_archive(sources)
    second = build_source_archive(tuple(reversed(sources)))
    resolved = read_source_archive(first)

    assert first == second
    assert [(item.relative_path, item.content) for item in resolved] == [
        ("a.txt", b"first\n"),
        ("nested/b.txt", b"second\n"),
    ]


def test_source_archive_rejects_tampered_retained_bytes() -> None:
    payload = bytearray(build_source_archive((_source("evidence.txt", b"evidence"),)))
    payload[-1] ^= 1

    with pytest.raises(SourceArchiveError, match="digest is invalid"):
        read_source_archive(bytes(payload))
