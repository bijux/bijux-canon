# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
import shutil

import pytest

from bijux_canon_ingest import (
    AdmissionResult,
    DiscoveryPolicy,
    DiscoveryRoot,
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
    ParsedTextDocument,
    admit_source,
    build_document_span_mappings,
    chunk_document_mappings,
    discover_sources,
    parse_docx,
    parse_html,
    parse_jats,
    parse_markdown,
    parse_pdf,
    parse_text,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource

Parsed = (
    ParsedDocument
    | ParsedDocxDocument
    | ParsedHtmlDocument
    | ParsedPdfDocument
    | ParsedTextDocument
)

REPOSITORY = Path(__file__).parents[4]
CORPUS = REPOSITORY / "examples" / "document-formats" / "corpus"
SOURCES: dict[SourceFormat, Path] = {
    "jats": CORPUS / "parser-jats-real.xml",
    "pdf-digital": CORPUS / "parser-pdf-digital-real.pdf",
    "html": CORPUS / "parser-html-real.html",
    "markdown": CORPUS / "parser-markdown-real.md",
    "text": CORPUS / "parser-text-real.txt",
    "docx": CORPUS / "parser-docx-real.docx",
}
PARSERS: dict[SourceFormat, Callable[[AdmissionResult], Parsed]] = {
    "jats": parse_jats,
    "pdf-digital": parse_pdf,
    "html": parse_html,
    "markdown": parse_markdown,
    "text": parse_text,
    "docx": parse_docx,
}


def _chunks(source: DiscoveredSource, format_id: SourceFormat) -> tuple[str, ...]:
    admission = admit_source(source)
    assert admission.admitted and admission.format_id == format_id
    document = PARSERS[format_id](admission)
    content = source.filesystem_path.read_bytes()
    mappings = build_document_span_mappings(content, document)
    return tuple(
        chunk.chunk_id for chunk in chunk_document_mappings(document, mappings)
    )


@pytest.mark.parametrize("format_id", tuple(SOURCES))
def test_duplicates_and_symlinks_preserve_aliases_without_duplicate_chunks(
    format_id: SourceFormat,
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    canonical_directory = root / "a"
    canonical_directory.mkdir(parents=True)
    suffix = SOURCES[format_id].suffix
    canonical_path = canonical_directory / f"source{suffix}"
    regular_alias = root / f"z-copy{suffix}"
    symlink_alias = root / f"y-link{suffix}"
    shutil.copyfile(SOURCES[format_id], canonical_path)
    shutil.copyfile(SOURCES[format_id], regular_alias)
    try:
        symlink_alias.symlink_to(canonical_path)
    except OSError as error:
        pytest.skip(f"filesystem does not support test symlinks: {error}")

    result = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot("research", root),),
            symlink_policy="files_within_root",
        )
    )
    canonical = tuple(
        source for source in result.sources if source.duplicate_of_location_id is None
    )
    aliases = tuple(
        source
        for source in result.sources
        if source.duplicate_of_location_id is not None
    )

    assert result.complete
    assert len(canonical) == 1
    assert len(aliases) == 2
    assert {source.content_sha256 for source in result.sources} == {
        canonical[0].content_sha256
    }
    assert len({source.location_id for source in result.sources}) == 3
    assert all(
        alias.duplicate_of_location_id == canonical[0].location_id for alias in aliases
    )
    link = next(source for source in aliases if source.is_symlink)
    assert link.target_relative_path == f"a/source{suffix}"

    emitted_chunk_ids = [
        chunk_id for source in canonical for chunk_id in _chunks(source, format_id)
    ]
    assert emitted_chunk_ids
    assert len(emitted_chunk_ids) == len(set(emitted_chunk_ids))


@pytest.mark.parametrize("format_id", tuple(SOURCES))
def test_rename_changes_location_identity_but_not_content_or_chunks(
    format_id: SourceFormat,
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    suffix = SOURCES[format_id].suffix
    original_path = root / f"before{suffix}"
    renamed_path = root / f"after{suffix}"
    shutil.copyfile(SOURCES[format_id], original_path)
    policy = DiscoveryPolicy(roots=(DiscoveryRoot("research", root),))

    before = discover_sources(policy).sources[0]
    before_chunk_ids = _chunks(before, format_id)
    original_path.rename(renamed_path)
    after = discover_sources(policy).sources[0]
    after_chunk_ids = _chunks(after, format_id)

    assert before.relative_path == f"before{suffix}"
    assert after.relative_path == f"after{suffix}"
    assert before.location_id != after.location_id
    assert before.content_sha256 == after.content_sha256
    assert before_chunk_ids == after_chunk_ids
