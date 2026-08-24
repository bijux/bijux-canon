# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from collections.abc import Callable
from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    AdmissionResult,
    DiscoveredSource,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    SemanticChunkingPolicy,
    admit_source,
    build_document_span_mappings,
    chunk_document_mappings,
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


def _parse(format_id: SourceFormat) -> tuple[bytes, Parsed]:
    receipt = json.loads(
        (
            EXAMPLES / "acquisition-receipts" / f"parser-{format_id}-real.json"
        ).read_text()
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
    return content, PARSERS[format_id](admission)


@pytest.mark.parametrize("format_id", tuple(PARSERS))
def test_chunks_real_documents_with_stable_bounded_lineage(
    format_id: SourceFormat,
) -> None:
    content, document = _parse(format_id)
    mappings = build_document_span_mappings(content, document)
    policy = SemanticChunkingPolicy(max_characters=480, overlap_characters=48)

    chunks = chunk_document_mappings(document, mappings, policy=policy)
    repeated = chunk_document_mappings(document, mappings, policy=policy)

    assert chunks == repeated
    assert chunks
    assert [chunk.chunk_index for chunk in chunks] == list(range(len(chunks)))
    assert all(0 < chunk.character_count <= policy.max_characters for chunk in chunks)
    assert all(chunk.token_count > 0 for chunk in chunks)
    assert all(chunk.mappings for chunk in chunks)
    assert all(
        mapping.resolve_source_bytes(content) == content
        for chunk in chunks
        for mapping in chunk.mappings
    )
    assert len({chunk.chunk_id for chunk in chunks}) == len(chunks)
    assert chunks[0].manifest() == chunks[0].manifest()


def test_oversized_semantic_block_uses_boundary_aligned_overlap() -> None:
    content, document = _parse("text")
    mappings = build_document_span_mappings(content, document)
    policy = SemanticChunkingPolicy(max_characters=100, overlap_characters=20)
    chunks = chunk_document_mappings(document, mappings, policy=policy)
    overlapping = [chunk for chunk in chunks if chunk.overlap_character_count]

    assert overlapping
    assert all(0 < chunk.overlap_character_count <= 20 for chunk in overlapping)
    for previous, current in zip(chunks, chunks[1:], strict=False):
        if current.overlap_character_count:
            overlap = current.overlap_character_count
            assert (
                previous.normalized_text[-overlap:] == current.normalized_text[:overlap]
            )


def test_oversized_paragraph_keeps_answer_sentences_whole() -> None:
    path = (
        REPOSITORY
        / "examples"
        / "ancient-dna-research"
        / "corpus"
        / "sources"
        / "plos-pbio-3000166.xml"
    )
    content = path.read_bytes()
    source = DiscoveredSource.create(
        root_name="ancient-dna-research",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type="application/xml",
        is_symlink=False,
    )
    admission = admit_source(source)
    assert admission.admitted
    document = parse_jats(admission)
    mappings = build_document_span_mappings(content, document)
    policy = SemanticChunkingPolicy(boundary_strategy="sentence")
    chunks = chunk_document_mappings(document, mappings, policy=policy)

    authenticity_sentence = (
        "Other hallmarks of RNA sequencing (RNA-seq) data such as exon-exon "
        "junction presence and high endogenous ribosomal RNA (rRNA) content "
        "confirms our data’s authenticity."
    )
    replication_sentence = (
        "By performing independent technical library replicates using two "
        "high-throughput sequencing platforms, we show not only that aRNA can "
        "survive for extended periods in mammalian tissues but also that it has "
        "potential for tissue identification."
    )

    assert any(authenticity_sentence in chunk.normalized_text for chunk in chunks)
    assert any(replication_sentence in chunk.normalized_text for chunk in chunks)
    assert policy.manifest() == {
        "block_separator": "\n\n",
        "boundary_strategy": "sentence",
        "max_characters": 1_200,
        "overlap_characters": 120,
        "schema_version": "bijux.canon.ingest.semantic_chunking_policy.v2",
    }


def test_default_policy_preserves_reviewed_v1_chunk_identities() -> None:
    research_root = REPOSITORY / "examples" / "ancient-dna-research"
    qrels = tuple(
        json.loads(line)
        for line in (research_root / "truth" / "qrels.jsonl").read_text().splitlines()
    )
    reviewed_by_source: dict[str, set[str]] = {}
    for qrel in qrels:
        reviewed_by_source.setdefault(qrel["source_sha256"], set()).add(
            qrel["chunk"]["chunk_id"]
        )

    observed_by_source: dict[str, set[str]] = {}
    for path in sorted((research_root / "corpus" / "sources").glob("*.xml")):
        content = path.read_bytes()
        source_sha256 = hashlib.sha256(content).hexdigest()
        source = DiscoveredSource.create(
            root_name="ancient-dna-research",
            relative_path=path.name,
            filesystem_path=path,
            content_sha256=source_sha256,
            byte_length=len(content),
            media_type="application/xml",
            is_symlink=False,
        )
        admission = admit_source(source)
        assert admission.admitted
        document = parse_jats(admission)
        mappings = build_document_span_mappings(content, document)
        observed_by_source[source_sha256] = {
            chunk.chunk_id for chunk in chunk_document_mappings(document, mappings)
        }

    assert SemanticChunkingPolicy().manifest() == {
        "block_separator": "\n\n",
        "max_characters": 1_200,
        "overlap_characters": 120,
        "schema_version": "bijux.canon.ingest.semantic_chunking_policy.v1",
    }
    assert reviewed_by_source.keys() == observed_by_source.keys()
    assert all(
        reviewed_by_source[source_sha256] <= observed_by_source[source_sha256]
        for source_sha256 in reviewed_by_source
    )


def test_canonical_fingerprint_does_not_depend_on_source_bytes() -> None:
    content, document = _parse("markdown")
    mappings = build_document_span_mappings(content, document)
    chunk = chunk_document_mappings(document, mappings)[0]
    relocated_mappings = []
    for mapping in chunk.mappings:
        relocated_span = replace(
            mapping.source_span,
            selected_bytes_sha256="0" * 64,
        )
        relocated_transformations = (
            replace(
                mapping.transformations[0],
                input_content_sha256="0" * 64,
            ),
            *mapping.transformations[1:],
        )
        relocated_mappings.append(
            replace(
                mapping,
                source_content_sha256="0" * 64,
                source_span=relocated_span,
                transformations=relocated_transformations,
            )
        )
    relocated = replace(
        chunk,
        source_content_sha256="0" * 64,
        mappings=tuple(relocated_mappings),
    )

    assert relocated.canonical_fingerprint == chunk.canonical_fingerprint
    assert relocated.chunk_id != chunk.chunk_id


def test_chunking_rejects_misaligned_mappings() -> None:
    content, document = _parse("docx")
    mappings = build_document_span_mappings(content, document)

    with pytest.raises(ValueError, match="align exactly"):
        chunk_document_mappings(document, mappings[:-1])


def test_smallest_valid_budget_remains_deterministic() -> None:
    content, document = _parse("jats")
    assert isinstance(document, ParsedDocument)
    single_block_document = replace(document, blocks=document.blocks[:1])
    mappings = build_document_span_mappings(content, document)
    policy = SemanticChunkingPolicy(max_characters=1, overlap_characters=0)
    chunks = chunk_document_mappings(
        single_block_document,
        mappings[:1],
        policy=policy,
    )

    assert all(chunk.character_count == 1 for chunk in chunks)


@pytest.mark.parametrize(
    "values",
    [
        {"max_characters": 0},
        {"max_characters": 10, "overlap_characters": 10},
        {"max_characters": 10, "overlap_characters": -1},
        {"max_characters": True},
        {"boundary_strategy": "paragraph"},
    ],
)
def test_chunking_policy_rejects_invalid_budgets(values: dict[str, object]) -> None:
    with pytest.raises(ValueError):
        SemanticChunkingPolicy(**values)
