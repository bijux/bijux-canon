# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from bijux_canon_ingest.application.source_metadata import (
    SourceMetadataRecord,
    normalize_source_metadata,
)
from bijux_canon_ingest.domain.source_admission import SourceFormat
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource

REPOSITORY = Path(__file__).parents[4]
EXAMPLES = REPOSITORY / "examples" / "document-formats"
FORMAT_IDS: tuple[SourceFormat, ...] = (
    "jats",
    "pdf-digital",
    "html",
    "markdown",
    "text",
    "docx",
)


def _source(
    format_id: SourceFormat,
) -> tuple[DiscoveredSource, dict[str, object], dict[str, object]]:
    identifier = f"parser-{format_id}-real"
    record = json.loads((EXAMPLES / "sources" / f"{identifier}.json").read_text())
    receipt = json.loads(
        (EXAMPLES / "acquisition-receipts" / f"{identifier}.json").read_text()
    )
    path = EXAMPLES / str(receipt["local_path"])
    content = path.read_bytes()
    source = DiscoveredSource.create(
        root_name="parser-corpus",
        relative_path=str(receipt["local_path"]),
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=str(receipt["media_type"]),
        is_symlink=False,
    )
    assert source.content_sha256 == receipt["sha256"]
    return source, record, receipt


@pytest.mark.parametrize("format_id", FORMAT_IDS)
def test_normalizes_real_admitted_source_metadata(format_id: SourceFormat) -> None:
    source, values, receipt = _source(format_id)

    result = normalize_source_metadata(
        source,
        format_id=format_id,
        records=(
            SourceMetadataRecord.from_mapping(
                values,
                provenance=f"source-record:{values['parser_source_id']}",
            ),
            SourceMetadataRecord.from_mapping(
                receipt,
                provenance=f"acquisition-receipt:{values['parser_source_id']}",
            ),
        ),
    )

    assert result.format_id == format_id
    assert result.title == values["title"]
    assert result.authors == tuple(values["authors"])
    assert result.publication_date == values["publication_date"]
    assert result.canonical_uri == values["canonical_uri"]
    assert result.license_expression == values["license"]["expression"]
    assert result.relative_path == source.relative_path
    assert result.media_type == source.media_type
    assert not result.conflicts
    assert result.manifest() == result.manifest()


def test_canonicalizes_equivalent_values_without_identity_loss() -> None:
    source, _, _ = _source("jats")
    result = normalize_source_metadata(
        source,
        format_id="jats",
        records=(
            SourceMetadataRecord(
                provenance="catalog",
                doi="https://doi.org/10.1371/JOURNAL.PBIO.3000166",
                canonical_uri="HTTPS://DOI.ORG:443/10.1371/journal.pbio.3000166",
                authors=(" Oliver  Smith ", "OLIVER SMITH", "Hervé Bocherens"),
                publication_date="2019-07-30T12:45:00Z",
                title=" Ancient RNA\nfrom canids ",
                journal=" PLOS  Biology ",
                language="EN_us",
                license_expression="cc-by-4.0",
                license_url="HTTPS://CREATIVECOMMONS.ORG:443/licenses/by/4.0/",
            ),
            SourceMetadataRecord(
                provenance="embedded-jats",
                doi="10.1371/journal.pbio.3000166",
                publication_date="2019",
            ),
        ),
    )

    assert result.doi == "10.1371/journal.pbio.3000166"
    assert result.canonical_uri == "https://doi.org/10.1371/journal.pbio.3000166"
    assert result.authors == ("Oliver Smith", "Hervé Bocherens")
    assert result.publication_date == "2019-07-30"
    assert result.title == "Ancient RNA from canids"
    assert result.journal == "PLOS Biology"
    assert result.language == "en-US"
    assert result.license_expression == "CC-BY-4.0"
    assert result.license_url == "https://creativecommons.org/licenses/by/4.0/"
    assert not result.conflicts
    assert any(
        raw.value == "https://doi.org/10.1371/JOURNAL.PBIO.3000166"
        for raw in result.raw_values
    )


def test_retains_deterministic_conflict_provenance() -> None:
    source, _, _ = _source("text")
    first = SourceMetadataRecord(
        provenance="curated-record",
        title="HTTP Semantics",
        canonical_uri="https://doi.org/10.17487/RFC9110",
    )
    second = SourceMetadataRecord(
        provenance="embedded-header",
        title="HTTP Core Semantics",
        canonical_uri="https://www.rfc-editor.org/rfc/rfc9110",
    )

    result = normalize_source_metadata(
        source,
        format_id="text",
        records=(first, second),
    )

    assert result.title == "HTTP Semantics"
    assert result.canonical_uri == "https://doi.org/10.17487/RFC9110"
    assert [conflict.field for conflict in result.conflicts] == [
        "canonical_uri",
        "title",
    ]
    title_conflict = result.conflicts[1]
    assert title_conflict.selected.provenance == "curated-record"
    assert title_conflict.alternatives[0].provenance == "embedded-header"


@pytest.mark.parametrize(
    ("record", "message"),
    [
        (SourceMetadataRecord(provenance="bad", doi="not-a-doi"), "DOI"),
        (
            SourceMetadataRecord(provenance="bad", canonical_uri="relative/path"),
            "absolute",
        ),
        (
            SourceMetadataRecord(provenance="bad", publication_date="2025-02-30"),
            "day is out of range",
        ),
        (
            SourceMetadataRecord(provenance="bad", relative_path="../escape.txt"),
            "parent segments",
        ),
        (
            SourceMetadataRecord(provenance="bad", media_type="invalid"),
            "type/subtype",
        ),
    ],
)
def test_rejects_invalid_identity_values(
    record: SourceMetadataRecord,
    message: str,
) -> None:
    source, _, _ = _source("text")
    with pytest.raises(ValueError, match=message):
        normalize_source_metadata(source, format_id="text", records=(record,))


def test_discovery_path_and_media_conflicts_are_visible() -> None:
    source, _, _ = _source("markdown")
    result = normalize_source_metadata(
        source,
        format_id="markdown",
        records=(
            SourceMetadataRecord(
                provenance="stale-catalog",
                relative_path="archive/old.md",
                media_type="text/markdown; charset=utf-8",
            ),
        ),
    )

    assert result.relative_path == source.relative_path
    assert result.media_type == source.media_type
    assert [conflict.field for conflict in result.conflicts] == [
        "media_type",
        "relative_path",
    ]
    assert all(
        conflict.selected.provenance == "source-discovery"
        and conflict.alternatives[0].provenance == "stale-catalog"
        for conflict in result.conflicts
    )
