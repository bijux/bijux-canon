"""Policy, safety, and restart checks for parser-source acquisition."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from urllib.error import HTTPError
from urllib.request import Request
import zipfile

import pytest

from bijux_canon_dev.corpus.parser_sources import (
    acquire_record,
    canonical,
    jpeg_dimensions,
    load_portfolio,
    open_with_retry,
    read_bounded,
    sha256,
    transform_html_article,
    validate_receipt_identity,
    validate_media,
    write_exclusive,
)


def _record(format_id: str) -> dict[str, object]:
    return {
        "schema_version": "bijux.canon.parser_source.v1",
        "parser_source_id": f"parser-{format_id}-real",
        "format_id": format_id,
        "acquisition": {
            "request_url": "https://example.test/source",
            "approved_origins": ["https://example.test"],
            "expected_media_types": ["text/plain"],
            "maximum_bytes": 4096,
        },
        "license": {
            "expression": "Apache-2.0",
            "evidence_uri": "https://example.test/license",
        },
        "redistribution": {"permitted": True},
        "format_requirements": {},
        "transformations": [],
        "attribution": "Example",
        "access_terms": "public",
    }


def test_bounded_reader_rejects_header_and_stream_overflow() -> None:
    assert read_bounded(BytesIO(b"abc"), maximum_bytes=3, content_length="3") == b"abc"
    with pytest.raises(ValueError, match="Content-Length"):
        read_bounded(BytesIO(b"abc"), maximum_bytes=2, content_length="3")
    with pytest.raises(ValueError, match="byte ceiling"):
        read_bounded(BytesIO(b"abc"), maximum_bytes=2, content_length=None)


def test_markdown_requires_all_declared_semantic_structures() -> None:
    record = _record("markdown")
    valid = b"# Title\n\n- item\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n```sh\necho ok\n```\n\n[link](https://example.test)\n"
    assert validate_media(record, valid)["table_rows"] == 3
    with pytest.raises(ValueError, match="semantic structure"):
        validate_media(record, b"# Title\n\nA paragraph only.\n")


def test_text_requires_substantive_rfc_identity() -> None:
    record = _record("text")
    record["format_requirements"] = {"minimum_lines": 1000}
    valid = ("RFC 9110 HTTP Semantics\n" + "content\n" * 1000).encode()
    assert validate_media(record, valid)["lines"] == 1001
    with pytest.raises(ValueError, match="identity or size"):
        validate_media(record, b"RFC 9110 HTTP Semantics\n")


def test_docx_rejects_unsafe_or_incomplete_packages() -> None:
    record = _record("docx")
    record["format_requirements"] = {
        "required_package_parts": ["[Content_Types].xml", "word/document.xml"]
    }
    output = BytesIO()
    with zipfile.ZipFile(output, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("../escape", "unsafe")
        package.writestr("word/document.xml", "<document/>")
    with pytest.raises(ValueError, match="unsafe path"):
        validate_media(record, output.getvalue())


def test_docx_requires_every_declared_semantic_structure() -> None:
    record = _record("docx")
    record["format_requirements"] = {
        "required_package_parts": ["[Content_Types].xml", "word/document.xml"]
    }
    output = BytesIO()
    document = (
        '<w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
        "<w:body><w:p><w:r><w:t>" + ("substantive " * 100) + "</w:t></w:r></w:p>"
        "<w:tbl/></w:body></w:document>"
    )
    with zipfile.ZipFile(output, "w") as package:
        package.writestr("[Content_Types].xml", "<Types/>")
        package.writestr("word/document.xml", document)
    with pytest.raises(ValueError, match="declared semantic structure"):
        validate_media(record, output.getvalue())


def test_html_transformation_keeps_article_and_removes_interface_code() -> None:
    source = b"""<html><head>
<meta name="citation_title" content="Article title">
<meta name="citation_author" content="Author name">
<meta name="citation_doi" content="10.1371/journal.pbio.3000166">
</head><body><nav>global</nav><section class="article-body">
<ul class="article-tabs"><li>Metrics</li></ul><h2>Abstract</h2>
<p>licensed article text</p><script>unsafe()</script><img src="asset.jpg">
</section><footer>global</footer></body></html>"""
    transformed = transform_html_article(source)
    assert b"licensed article text" in transformed
    assert b"citation_doi" in transformed
    assert b"global" not in transformed
    assert b"unsafe" not in transformed
    assert b"asset.jpg" not in transformed


def test_http_retry_is_bounded_for_transient_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    attempts = 0
    terminal = object()

    def fake_open(*args: object, **kwargs: object) -> object:
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise HTTPError(
                "https://example.test", 429, "retry", {"Retry-After": "0"}, None
            )
        return terminal

    monkeypatch.setattr("urllib.request.urlopen", fake_open)
    assert open_with_retry(Request("https://example.test")) is terminal
    assert attempts == 3


def test_jpeg_dimensions_rejects_non_jpeg() -> None:
    with pytest.raises(ValueError, match="not a JPEG"):
        jpeg_dimensions(b"not an image")


def test_portfolio_requires_exact_canonical_format_set(tmp_path: Path) -> None:
    portfolio = tmp_path / "sources.jsonl"
    portfolio.write_bytes(canonical(_record("markdown")) + b"\n")
    with pytest.raises(ValueError, match="exactly seven"):
        load_portfolio(portfolio)


def test_exclusive_write_is_restart_safe_and_immutable(tmp_path: Path) -> None:
    target = tmp_path / "source.bin"
    write_exclusive(target, b"same")
    write_exclusive(target, b"same")
    assert target.stat().st_mode & 0o222 == 0
    with pytest.raises(RuntimeError, match="different durable bytes"):
        write_exclusive(target, b"different")


def test_existing_receipt_replays_without_network(tmp_path: Path) -> None:
    record = _record("markdown")
    record["parser_source_id"] = "parser-markdown-real"
    body = b"# Title\n\n- item\n\n| A | B |\n| - | - |\n| 1 | 2 |\n\n```sh\necho ok\n```\n\n[link](https://example.test)\n"
    source_identity = sha256(canonical(record))
    media = tmp_path / "media/parser-markdown-real.md"
    source = tmp_path / "sources/parser-markdown-real.json"
    receipt = tmp_path / "acquisition-receipts/parser-markdown-real.json"
    write_exclusive(media, body)
    receipt_core = {
        "schema_version": "bijux.canon.parser_source_acquisition.v1",
        "parser_source_id": "parser-markdown-real",
        "format_id": "markdown",
        "source_record_identity_sha256": source_identity,
        "state": "acquired",
        "media_type": "text/plain",
        "sha256": sha256(body),
        "byte_count": len(body),
        "local_path": "media/parser-markdown-real.md",
        "license": record["license"],
        "license_evidence": {},
        "attribution": record["attribution"],
        "access_terms": record["access_terms"],
        "redistribution": record["redistribution"],
        "transformations": [],
        "inspection": validate_media(record, body),
        "transport": {},
    }
    receipt_value = {
        **receipt_core,
        "retrieved_at": "2026-08-21T00:00:00Z",
        "receipt_identity_sha256": sha256(canonical(receipt_core)),
    }
    write_exclusive(receipt, canonical(receipt_value) + b"\n")
    assert acquire_record(record, output_root=tmp_path) == receipt_value
    assert json.loads(source.read_text())["record_identity_sha256"] == source_identity


def test_receipt_identity_rejects_tampering() -> None:
    receipt = {
        "parser_source_id": "parser-markdown-real",
        "retrieved_at": "2026-08-21T00:00:00Z",
        "receipt_identity_sha256": "0" * 64,
    }
    with pytest.raises(RuntimeError, match="identity mismatch"):
        validate_receipt_identity(receipt)
