# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Plan and verify deterministic incremental corpus transitions."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from bijux_canon_ingest.application.corpus_snapshot import build_corpus_snapshot
from bijux_canon_ingest.domain.corpus_delta import (
    CorpusDelta,
    SourceModification,
    SourceRename,
    SourceTombstone,
    TombstoneReason,
)
from bijux_canon_ingest.domain.corpus_snapshot import (
    CorpusSnapshot,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
)
from bijux_canon_ingest.domain.source_admission import AdmissionResult


def _chunks(document: CorpusSnapshotDocument) -> tuple[str, ...]:
    return tuple(sorted(chunk.chunk_id for chunk in document.chunks))


def _document_signature(document: CorpusSnapshotDocument) -> tuple[object, ...]:
    return (
        document.admission.source.content_sha256,
        document.document_id,
        _chunks(document),
    )


def _rename_signature(document: CorpusSnapshotDocument) -> tuple[object, ...]:
    return (
        document.admission.source.content_sha256,
        document.document.manifest()["manifest_sha256"],
        _chunks(document),
    )


def _tombstone(
    document: CorpusSnapshotDocument,
    *,
    reason: TombstoneReason,
) -> SourceTombstone:
    source = document.admission.source
    return SourceTombstone(
        root_name=source.root_name,
        relative_path=source.relative_path,
        location_id=source.location_id,
        content_sha256=source.content_sha256,
        document_id=document.document_id,
        chunk_ids=_chunks(document),
        reason=reason,
    )


def _rejection_ids(snapshot: CorpusSnapshot) -> set[str]:
    return {
        str(rejection.manifest()["manifest_sha256"])
        for rejection in snapshot.rejections
    }


def plan_corpus_delta(
    previous: CorpusSnapshot,
    current: CorpusSnapshot,
) -> CorpusDelta:
    """Classify a canonical snapshot transition and its index invalidations."""

    previous_by_location = {
        item.admission.source.location_id: item for item in previous.documents
    }
    current_by_location = {
        item.admission.source.location_id: item for item in current.documents
    }
    shared_locations = set(previous_by_location) & set(current_by_location)
    modifications: list[SourceModification] = []
    for location_id in sorted(shared_locations):
        before = previous_by_location[location_id]
        after = current_by_location[location_id]
        if _document_signature(before) == _document_signature(after):
            continue
        modifications.append(
            SourceModification(
                location_id=location_id,
                relative_path=after.admission.source.relative_path,
                previous_content_sha256=before.admission.source.content_sha256,
                current_content_sha256=after.admission.source.content_sha256,
                previous_document_id=before.document_id,
                current_document_id=after.document_id,
            )
        )

    removed = {
        location_id: document
        for location_id, document in previous_by_location.items()
        if location_id not in current_by_location
    }
    added = {
        location_id: document
        for location_id, document in current_by_location.items()
        if location_id not in previous_by_location
    }
    added_by_signature: dict[tuple[object, ...], list[CorpusSnapshotDocument]] = (
        defaultdict(list)
    )
    for document in added.values():
        added_by_signature[_rename_signature(document)].append(document)
    for values in added_by_signature.values():
        values.sort(key=lambda item: item.admission.source.location_id)

    renames: list[SourceRename] = []
    renamed_previous: set[str] = set()
    renamed_current: set[str] = set()
    for previous_location, before in sorted(removed.items()):
        matches = added_by_signature.get(_rename_signature(before), [])
        renamed_document = next(
            (
                candidate
                for candidate in matches
                if candidate.admission.source.location_id not in renamed_current
            ),
            None,
        )
        if renamed_document is None:
            continue
        renamed_previous.add(previous_location)
        renamed_current.add(renamed_document.admission.source.location_id)
        renames.append(
            SourceRename(
                previous_location_id=previous_location,
                current_location_id=renamed_document.admission.source.location_id,
                previous_relative_path=before.admission.source.relative_path,
                current_relative_path=renamed_document.admission.source.relative_path,
                content_sha256=before.admission.source.content_sha256,
                previous_document_id=before.document_id,
                current_document_id=renamed_document.document_id,
            )
        )

    deleted = [
        document
        for location_id, document in removed.items()
        if location_id not in renamed_previous
    ]
    newly_added = [
        document
        for location_id, document in added.items()
        if location_id not in renamed_current
    ]
    modified_before = [
        previous_by_location[change.location_id] for change in modifications
    ]
    modified_after = [
        current_by_location[change.location_id] for change in modifications
    ]
    tombstones = [
        *(_tombstone(document, reason="deleted") for document in deleted),
        *(_tombstone(document, reason="modified") for document in modified_before),
    ]
    previous_rejections = _rejection_ids(previous)
    current_rejections = _rejection_ids(current)
    return CorpusDelta(
        previous_snapshot_id=previous.snapshot_id,
        current_snapshot_id=current.snapshot_id,
        added_document_ids=tuple(
            sorted(document.document_id for document in newly_added)
        ),
        deleted_document_ids=tuple(
            sorted(document.document_id for document in deleted)
        ),
        modifications=tuple(modifications),
        renames=tuple(
            sorted(
                renames,
                key=lambda item: (
                    item.previous_location_id,
                    item.current_location_id,
                ),
            )
        ),
        tombstones=tuple(
            sorted(tombstones, key=lambda item: (item.location_id, item.reason))
        ),
        added_chunk_ids=tuple(
            sorted(
                {
                    chunk_id
                    for document in (*newly_added, *modified_after)
                    for chunk_id in _chunks(document)
                }
            )
        ),
        invalidated_chunk_ids=tuple(
            sorted(
                {
                    chunk_id
                    for document in (*deleted, *modified_before)
                    for chunk_id in _chunks(document)
                }
            )
        ),
        added_rejection_ids=tuple(sorted(current_rejections - previous_rejections)),
        removed_rejection_ids=tuple(sorted(previous_rejections - current_rejections)),
    )


def apply_corpus_delta(
    previous: CorpusSnapshot,
    delta: CorpusDelta,
    configuration: CorpusSnapshotConfiguration,
    documents: Iterable[CorpusSnapshotDocument],
    *,
    rejections: Iterable[AdmissionResult] = (),
) -> CorpusSnapshot:
    """Build the target and require exact equivalence with the declared delta."""

    if previous.snapshot_id != delta.previous_snapshot_id:
        raise ValueError("corpus delta does not start from the supplied snapshot")
    target = build_corpus_snapshot(
        configuration,
        documents,
        rejections=rejections,
    )
    observed = plan_corpus_delta(previous, target)
    if observed != delta:
        raise ValueError(
            "incremental inputs do not reproduce the declared corpus delta"
        )
    return target


__all__ = ["apply_corpus_delta", "plan_corpus_delta"]
