# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical corpus snapshot assembly."""

from __future__ import annotations

from collections.abc import Iterable

from bijux_canon_ingest.domain.corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
)
from bijux_canon_ingest.domain.source_admission import AdmissionResult


def _source_order(admission: AdmissionResult) -> tuple[str, str, str]:
    return (
        admission.source.root_name,
        admission.source.relative_path,
        admission.source.content_sha256,
    )


def build_corpus_snapshot(
    configuration: CorpusSnapshotConfiguration,
    documents: Iterable[CorpusSnapshotDocument],
    *,
    rejections: Iterable[AdmissionResult] = (),
) -> CorpusSnapshot:
    """Assemble iteration-order-independent canonical corpus membership."""

    ordered_documents = tuple(
        sorted(documents, key=lambda item: _source_order(item.admission))
    )
    ordered_rejections = tuple(sorted(rejections, key=_source_order))
    return CorpusSnapshot(
        configuration=configuration,
        documents=ordered_documents,
        rejections=ordered_rejections,
    )


__all__ = ["build_corpus_snapshot"]
