"""Full-text validation tests for the durable JATS portfolio."""

from __future__ import annotations

from pathlib import Path
from typing import Any
import xml.etree.ElementTree as ET

import pytest

from bijux_canon_dev.corpus.acquisition import sha256
from bijux_canon_dev.corpus.materialization import (
    build_manifest,
    inspect_full_text,
    materialize_record,
    supplementary_links,
)

DOI = "10.1371/journal.pone.0021247"


def _jats(*, body: bool = True) -> bytes:
    paragraphs = "".join(
        f"<p>Paragraph {index} {'evidence ' * 40}</p>" for index in range(6)
    )
    body_xml = (
        f"<body><sec><title>Results</title>{paragraphs}</sec></body>" if body else ""
    )
    return (
        '<article article-type="research-article" xmlns:xlink="http://www.w3.org/1999/xlink">'
        "<front><article-meta>"
        f'<article-id pub-id-type="doi">{DOI}</article-id>'
        "<title-group><article-title>Reviewed title</article-title></title-group>"
        f"<abstract><p>{'abstract evidence ' * 80}</p></abstract>"
        "</article-meta></front>"
        f"{body_xml}"
        '<back><supplementary-material xlink:href="pone.0021247.s001.pdf"/>'
        '<related-object xlink:href="pone.0021247.s001.pdf"/></back>'
        "</article>"
    ).encode()


def _record() -> dict[str, Any]:
    return {
        "source_id": "plos-pone-0021247",
        "record_identity_sha256": "a" * 64,
        "doi": DOI,
        "title": "Reviewed title",
        "authors": ["A. Author"],
        "journal": "PLOS ONE",
        "publication_year": 2011,
        "license": {"expression": "CC BY 4.0", "url": "https://example.test/license"},
        "attribution": "A. Author (2011). Reviewed title.",
    }


def test_inspection_requires_substantive_full_text() -> None:
    result = inspect_full_text(_jats(), doi=DOI)
    assert result["body_paragraphs"] == 6
    assert result["body_sections"] == 1
    assert result["supplementary_links"] == ["pone.0021247.s001.pdf"]

    with pytest.raises(ValueError, match="exactly one body"):
        inspect_full_text(_jats(body=False), doi=DOI)


def test_supplementary_links_are_distinct_and_sorted() -> None:
    root = ET.fromstring(_jats())
    assert supplementary_links(root) == ["pone.0021247.s001.pdf"]


def test_materialization_preserves_exact_acquired_bytes(tmp_path: Path) -> None:
    record = _record()
    body = _jats()
    acquisition_root = tmp_path / "acquired"
    acquired_path = acquisition_root / "objects/source/article.xml"
    acquired_path.parent.mkdir(parents=True)
    acquired_path.write_bytes(body)
    receipt = {
        "source_id": record["source_id"],
        "source_record_identity_sha256": record["record_identity_sha256"],
        "local_path": "objects/source/article.xml",
        "byte_count": len(body),
        "sha256": sha256(body),
        "receipt_identity_sha256": "b" * 64,
        "media_type": "application/xml",
    }

    result = materialize_record(
        record,
        receipt,
        acquisition_root=acquisition_root,
        output_root=tmp_path / "portfolio",
    )

    output = tmp_path / "portfolio" / result["local_path"]
    assert output.read_bytes() == body
    assert result["transformations"] == []

    output.write_bytes(b"different")
    with pytest.raises(RuntimeError, match="refusing to replace"):
        materialize_record(
            record,
            receipt,
            acquisition_root=acquisition_root,
            output_root=tmp_path / "portfolio",
        )


def test_materialization_rejects_receipt_byte_drift(tmp_path: Path) -> None:
    record = _record()
    acquired = tmp_path / "objects/article.xml"
    acquired.parent.mkdir()
    acquired.write_bytes(_jats())
    receipt = {
        "source_id": record["source_id"],
        "source_record_identity_sha256": record["record_identity_sha256"],
        "local_path": "objects/article.xml",
        "byte_count": len(_jats()),
        "sha256": "c" * 64,
        "receipt_identity_sha256": "b" * 64,
        "media_type": "application/xml",
    }
    with pytest.raises(ValueError, match="do not match"):
        materialize_record(
            record,
            receipt,
            acquisition_root=tmp_path,
            output_root=tmp_path / "portfolio",
        )


def test_manifest_identity_is_order_independent() -> None:
    first = {
        "source_id": "b",
        "source_record_identity_sha256": "1" * 64,
        "acquisition_receipt_identity_sha256": "2" * 64,
        "sha256": "3" * 64,
    }
    second = {
        "source_id": "a",
        "source_record_identity_sha256": "4" * 64,
        "acquisition_receipt_identity_sha256": "5" * 64,
        "sha256": "6" * 64,
    }
    forward = build_manifest([first, second])
    reverse = build_manifest([second, first])
    assert forward == reverse
    assert [item["source_id"] for item in forward["sources"]] == ["a", "b"]
