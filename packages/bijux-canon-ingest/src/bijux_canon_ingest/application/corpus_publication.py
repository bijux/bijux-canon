# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application service for durable corpus snapshot activation."""

from __future__ import annotations

from pathlib import Path

from bijux_canon_ingest.domain.corpus_publication import (
    PublishedCorpusSnapshot,
    SnapshotRecovery,
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshot
from bijux_canon_ingest.infra.corpus_snapshot_store import CorpusSnapshotStore


def publish_corpus_snapshot(
    root: str | Path,
    snapshot: CorpusSnapshot,
) -> PublishedCorpusSnapshot:
    """Publish a canonical snapshot with manifest-last activation."""

    return CorpusSnapshotStore(root).publish(snapshot)


def read_published_corpus_snapshot(
    root: str | Path,
) -> PublishedCorpusSnapshot | None:
    """Read the active snapshot only after verifying its complete generation."""

    return CorpusSnapshotStore(root).read_active()


def recover_corpus_snapshot_store(root: str | Path) -> SnapshotRecovery:
    """Reconcile interrupted staging and restore the last admitted snapshot."""

    return CorpusSnapshotStore(root).recover()


__all__ = [
    "publish_corpus_snapshot",
    "read_published_corpus_snapshot",
    "recover_corpus_snapshot_store",
]
