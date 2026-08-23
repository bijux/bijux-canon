# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    AdmissionResult,
    CorpusSnapshotConfiguration,
    CorpusSnapshotDocument,
    DiscoveredSource,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    SemanticChunkingPolicy,
    SourceMetadataRecord,
    admit_source,
    build_corpus_snapshot,
    build_document_span_mappings,
    chunk_document_mappings,
    normalize_source_metadata,
    parse_docx,
    parse_html,
    parse_jats,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat

Parsed = (
    ParsedDocument
    | ParsedDocxDocument
    | ParsedHtmlDocument
    | ParsedPdfDocument
    | ParsedTextDocument
)

REPOSITORY = Path(__file__).parents[4]
EXAMPLES = REPOSITORY / "examples" / "document-formats"
PARSERS: dict[SourceFormat, Callable[[AdmissionResult], Parsed]] = {
    "jats": parse_jats,
    "pdf-digital": parse_pdf,
    "html": parse_html,
    "markdown": parse_markdown,
    "text": parse_text,
    "docx": parse_docx,
}
POLICY = SemanticChunkingPolicy(max_characters=480, overlap_characters=48)


def _snapshot_document(format_id: SourceFormat) -> CorpusSnapshotDocument:
    identifier = f"parser-{format_id}-real"
    source_record = json.loads(
        (EXAMPLES / "sources" / f"{identifier}.json").read_text()
    )
    receipt = json.loads(
        (EXAMPLES / "acquisition-receipts" / f"{identifier}.json").read_text()
    )
    path = EXAMPLES / receipt["local_path"]
    content = path.read_bytes()
    source = DiscoveredSource.create(
        root_name="parser-corpus",
        relative_path=receipt["local_path"],
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=(
            "text/markdown" if format_id == "markdown" else receipt["media_type"]
        ),
        is_symlink=False,
    )
    admission = admit_source(source)
    assert admission.admitted
    document = PARSERS[format_id](admission)
    metadata = normalize_source_metadata(
        source,
        format_id=format_id,
        records=(
            SourceMetadataRecord.from_mapping(
                source_record,
                provenance=f"source-record:{identifier}",
            ),
            SourceMetadataRecord.from_mapping(
                receipt,
                provenance=f"acquisition-receipt:{identifier}",
            ),
        ),
    )
    mappings = build_document_span_mappings(content, document)
    chunks = chunk_document_mappings(document, mappings, policy=POLICY)
    return CorpusSnapshotDocument(admission, document, metadata, mappings, chunks)


@pytest.fixture(scope="module")
def real_documents() -> tuple[CorpusSnapshotDocument, ...]:
    return tuple(_snapshot_document(format_id) for format_id in PARSERS)


def _rejection(path: Path) -> AdmissionResult:
    content = b"unsupported corpus payload"
    path.write_bytes(content)
    source = DiscoveredSource.create(
        root_name="parser-corpus",
        relative_path="rejected/source.bin",
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type="application/octet-stream",
        is_symlink=False,
    )
    result = admit_source(source)
    assert not result.admitted
    return result


def test_snapshot_serialization_is_canonical_across_input_order(
    real_documents: tuple[CorpusSnapshotDocument, ...],
    tmp_path: Path,
) -> None:
    configuration = CorpusSnapshotConfiguration(
        corpus_name="parser-qualification",
        chunking_policy=POLICY,
    )
    rejection = _rejection(tmp_path / "source.bin")

    snapshot = build_corpus_snapshot(
        configuration,
        real_documents,
        rejections=(rejection,),
    )
    reversed_snapshot = build_corpus_snapshot(
        configuration,
        reversed(real_documents),
        rejections=(rejection,),
    )

    assert snapshot.snapshot_id == reversed_snapshot.snapshot_id
    assert snapshot.canonical_bytes == reversed_snapshot.canonical_bytes
    assert json.loads(snapshot.canonical_bytes) == snapshot.manifest()
    assert snapshot.snapshot_id.startswith("sha256:")
    assert len(snapshot.documents) == 6
    assert len(snapshot.rejections) == 1
    assert all(document.chunks for document in snapshot.documents)
    assert all(document.mappings for document in snapshot.documents)
    assert all(
        len(document.citation_lineage.records) == len(document.chunks)
        for document in snapshot.documents
    )
    assert all(
        document.citation_lineage.document_id == document.document_id
        and document.citation_lineage.source_content_sha256
        == document.admission.source.content_sha256
        for document in snapshot.documents
    )
    assert all(
        raw_document["citation_lineage"]["lineage_sha256"].startswith("sha256:")
        for raw_document in snapshot.manifest()["documents"]
    )


def test_snapshot_identity_changes_with_declared_configuration(
    real_documents: tuple[CorpusSnapshotDocument, ...],
) -> None:
    first = build_corpus_snapshot(
        CorpusSnapshotConfiguration(
            corpus_name="parser-qualification",
            chunking_policy=POLICY,
        ),
        real_documents,
    )
    second = build_corpus_snapshot(
        CorpusSnapshotConfiguration(
            corpus_name="parser-release",
            chunking_policy=POLICY,
        ),
        real_documents,
    )

    assert first.snapshot_id != second.snapshot_id


def test_snapshot_rejects_duplicate_source_locations(
    real_documents: tuple[CorpusSnapshotDocument, ...],
) -> None:
    configuration = CorpusSnapshotConfiguration(
        corpus_name="parser-qualification",
        chunking_policy=POLICY,
    )
    with pytest.raises(ValueError, match="locations must be unique"):
        build_corpus_snapshot(
            configuration,
            (real_documents[0], real_documents[0]),
        )


@pytest.mark.parametrize("name", ["", "Uppercase", "contains spaces", ".hidden"])
def test_snapshot_configuration_rejects_nonportable_names(name: str) -> None:
    with pytest.raises(ValueError, match="corpus_name"):
        CorpusSnapshotConfiguration(corpus_name=name)
