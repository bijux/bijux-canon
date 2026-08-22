# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import hashlib
import io
from pathlib import Path
import zipfile

import pytest

from bijux_canon_ingest import (
    AdmissionBudgets,
    DiscoveredSource,
    admit_source,
    admit_sources,
)

_DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)


def _source(
    tmp_path: Path,
    name: str,
    content: bytes,
    media_type: str,
) -> DiscoveredSource:
    path = tmp_path / name
    path.write_bytes(content)
    return DiscoveredSource.create(
        root_name="research",
        relative_path=name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


def _pdf(*, pages: int = 1, encrypted: bool = False) -> bytes:
    page_objects = b"\n".join(
        f"{index + 3} 0 obj << /Type /Page /Parent 2 0 R >> endobj".encode()
        for index in range(pages)
    )
    encryption = b" /Encrypt 99 0 R" if encrypted else b""
    return b"".join(
        (
            b"%PDF-1.7\n",
            b"1 0 obj << /Type /Catalog /Pages 2 0 R >> endobj\n",
            f"2 0 obj << /Type /Pages /Count {pages} >> endobj\n".encode(),
            page_objects,
            b"\nstartxref\n0\n%%EOF\n",
            encryption,
            b"\nstartxref\n0\n%%EOF\n",
        )
    )


def _docx(
    *,
    document_text: str = "Evidence",
    extra_members: dict[str, bytes] | None = None,
) -> bytes:
    target = io.BytesIO()
    with zipfile.ZipFile(target, "w", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(
            "[Content_Types].xml",
            '<?xml version="1.0"?><Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
            '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
            "</Types>",
        )
        archive.writestr(
            "word/document.xml",
            '<?xml version="1.0"?><w:document xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main">'
            f"<w:body><w:p><w:r><w:t>{document_text}</w:t></w:r></w:p></w:body>"
            "</w:document>",
        )
        for name, content in (extra_members or {}).items():
            archive.writestr(name, content)
    return target.getvalue()


def _append_archive_member(
    content: bytes,
    name: str | zipfile.ZipInfo,
    payload: bytes,
) -> bytes:
    target = io.BytesIO(content)
    with zipfile.ZipFile(target, "a", compression=zipfile.ZIP_DEFLATED) as archive:
        archive.writestr(name, payload)
    return target.getvalue()


@pytest.mark.parametrize(
    ("name", "content", "declared_media_type", "format_id", "detected_media_type"),
    [
        (
            "article.xml",
            b"<?xml version='1.0'?><article><body><p>Evidence</p></body></article>",
            "application/xml",
            "jats",
            "application/jats+xml",
        ),
        (
            "paper.pdf",
            _pdf(),
            "application/pdf",
            "pdf-digital",
            "application/pdf",
        ),
        (
            "page.html",
            b"<!doctype html><html><body><main>Evidence</main></body></html>",
            "text/html",
            "html",
            "text/html",
        ),
        (
            "README.md",
            b"# Evidence\n",
            "text/markdown",
            "markdown",
            "text/plain",
        ),
        ("notes.txt", b"Evidence\n", "text/plain", "text", "text/plain"),
        (
            "scan.png",
            bytes.fromhex(
                "89504e470d0a1a0a0000000d49484452000000010000000108060000001f15c489"
                "0000000d49444154789c6360606060000000050001a5f645400000000049454e44"
                "ae426082"
            ),
            "image/png",
            "ocr-required",
            "image/png",
        ),
    ],
)
def test_admission_identifies_supported_bytes_and_declared_metadata(
    tmp_path: Path,
    name: str,
    content: bytes,
    declared_media_type: str,
    format_id: str,
    detected_media_type: str,
) -> None:
    source = _source(tmp_path, name, content, declared_media_type)

    first = admit_source(source)
    second = admit_source(source)

    assert first.admitted is True
    assert first.format_id == format_id
    assert first.evidence.detected_media_type == detected_media_type
    assert first.manifest() == second.manifest()


def test_admission_preflights_docx_archive_and_markup(tmp_path: Path) -> None:
    content = _docx()
    result = admit_source(_source(tmp_path, "paper.docx", content, _DOCX_MEDIA_TYPE))

    assert result.admitted is True
    assert result.format_id == "docx"
    assert result.evidence.detected_media_type == _DOCX_MEDIA_TYPE
    assert result.evidence.archive_member_count == 2
    assert result.evidence.archive_uncompressed_bytes is not None
    assert result.evidence.node_count == 7
    assert result.evidence.text_bytes == len("Evidence")


@pytest.mark.parametrize(
    ("name", "content", "media_type", "budgets", "issue_code"),
    [
        (
            "large.txt",
            b"12345",
            "text/plain",
            AdmissionBudgets(max_file_bytes=4),
            "file_budget_exceeded",
        ),
        (
            "text.txt",
            b"12345",
            "text/plain",
            AdmissionBudgets(max_text_bytes=4),
            "text_budget_exceeded",
        ),
        (
            "tree.xml",
            b"<article><body><p>one</p></body></article>",
            "application/xml",
            AdmissionBudgets(max_nodes=2),
            "node_budget_exceeded",
        ),
        (
            "pages.pdf",
            _pdf(pages=2),
            "application/pdf",
            AdmissionBudgets(max_pages=1),
            "page_budget_exceeded",
        ),
    ],
)
def test_admission_enforces_each_non_archive_resource_budget(
    tmp_path: Path,
    name: str,
    content: bytes,
    media_type: str,
    budgets: AdmissionBudgets,
    issue_code: str,
) -> None:
    result = admit_source(_source(tmp_path, name, content, media_type), budgets=budgets)

    assert result.admitted is False
    assert result.issues[0].code == issue_code


def test_admission_rejects_declared_type_conflicts_and_unknown_binary(
    tmp_path: Path,
) -> None:
    mismatch = admit_source(
        _source(tmp_path, "wrong.pdf", b"plain text", "application/pdf")
    )
    unknown = admit_source(
        _source(
            tmp_path,
            "unknown.bin",
            b"\x00\x01\x02\x03",
            "application/octet-stream",
        )
    )

    assert mismatch.issues[0].code == "media_type_mismatch"
    assert mismatch.evidence.detected_media_type == "text/plain"
    assert unknown.issues[0].code == "unsupported_input"
    assert unknown.evidence.detected_media_type is None


def test_admission_rejects_encrypted_and_malformed_pdf_inputs(
    tmp_path: Path,
) -> None:
    encrypted = admit_source(
        _source(tmp_path, "encrypted.pdf", _pdf(encrypted=True), "application/pdf")
    )
    malformed = admit_source(
        _source(tmp_path, "malformed.pdf", b"%PDF-1.7\n", "application/pdf")
    )

    assert encrypted.issues[0].code == "encrypted_input"
    assert malformed.issues[0].code == "malformed_input"


def test_admission_rejects_malformed_and_entity_bearing_xml(tmp_path: Path) -> None:
    malformed = admit_source(
        _source(tmp_path, "bad.xml", b"<article>", "application/xml")
    )
    entity = admit_source(
        _source(
            tmp_path,
            "entity.xml",
            b"<!DOCTYPE article [<!ENTITY x 'expanded'>]><article>&x;</article>",
            "application/xml",
        )
    )

    assert malformed.issues[0].code == "malformed_input"
    assert entity.issues[0].code == "unsafe_markup"


def test_admission_allows_only_external_standard_jats_document_types(
    tmp_path: Path,
) -> None:
    approved = admit_source(
        _source(
            tmp_path,
            "approved.xml",
            b'<!DOCTYPE article PUBLIC "-//NLM//DTD JATS Journal Publishing DTD v1.3 20210610//EN" '
            b'"https://jats.nlm.nih.gov/publishing/1.3/JATS-journalpublishing1-3.dtd">'
            b"<article><body><p>Evidence</p></body></article>",
            "application/xml",
        )
    )
    unapproved = admit_source(
        _source(
            tmp_path,
            "unapproved.xml",
            b'<!DOCTYPE article SYSTEM "https://example.com/article.dtd">'
            b"<article><body><p>Evidence</p></body></article>",
            "application/xml",
        )
    )

    assert approved.admitted is True
    assert approved.format_id == "jats"
    assert unapproved.issues[0].code == "unsafe_markup"


def test_admission_rejects_unsafe_and_oversized_docx_archives(
    tmp_path: Path,
) -> None:
    unsafe_content = _docx(extra_members={"../escape.xml": b"<escape/>"})
    unsafe = admit_source(
        _source(tmp_path, "unsafe.docx", unsafe_content, _DOCX_MEDIA_TYPE)
    )
    oversized_content = _docx(extra_members={"word/extra.xml": b"<extra/>"})
    oversized = admit_source(
        _source(tmp_path, "large.docx", oversized_content, _DOCX_MEDIA_TYPE),
        budgets=AdmissionBudgets(max_archive_members=2),
    )

    assert unsafe.issues[0].code == "unsafe_archive"
    assert oversized.issues[0].code == "archive_budget_exceeded"


@pytest.mark.parametrize(
    "member_name",
    [
        "/absolute.xml",
        "../escape.xml",
        "word/../escape.xml",
        "word/./document.xml",
        "word//document.xml",
        "word\\document.xml",
        "C:/document.xml",
    ],
)
def test_admission_rejects_nonportable_archive_member_names(
    tmp_path: Path,
    member_name: str,
) -> None:
    content = _append_archive_member(_docx(), member_name, b"<unsafe/>")

    result = admit_source(
        _source(tmp_path, "unsafe-name.docx", content, _DOCX_MEDIA_TYPE)
    )

    assert result.issues[0].code == "unsafe_archive"


def test_admission_rejects_duplicate_and_symlink_archive_members(
    tmp_path: Path,
) -> None:
    with pytest.warns(UserWarning, match="Duplicate name"):
        duplicate = _append_archive_member(
            _docx(), "word/document.xml", b"<w:document/>"
        )
    link = zipfile.ZipInfo("word/external-link")
    link.create_system = 3
    link.external_attr = (0o120777 << 16) | 0xA000
    symlink = _append_archive_member(_docx(), link, b"../../outside")

    duplicate_result = admit_source(
        _source(tmp_path, "duplicate.docx", duplicate, _DOCX_MEDIA_TYPE)
    )
    symlink_result = admit_source(
        _source(tmp_path, "symlink.docx", symlink, _DOCX_MEDIA_TYPE)
    )

    assert duplicate_result.issues[0].code == "unsafe_archive"
    assert symlink_result.issues[0].code == "unsafe_archive"


def test_admission_bounds_nested_archive_payloads_without_expansion(
    tmp_path: Path,
) -> None:
    nested = _append_archive_member(
        _docx(), "word/embeddings/archive.zip", b"PK\x03\x04" + b"x" * 10_000
    )

    result = admit_source(
        _source(tmp_path, "nested.docx", nested, _DOCX_MEDIA_TYPE),
        budgets=AdmissionBudgets(max_archive_compression_ratio=2.0),
    )

    assert result.issues[0].code == "archive_budget_exceeded"
    assert result.evidence.node_count is None


def test_admission_rejects_docx_compression_bombs_before_member_reads(
    tmp_path: Path,
) -> None:
    content = _docx(document_text="x" * 10_000)
    result = admit_source(
        _source(tmp_path, "bomb.docx", content, _DOCX_MEDIA_TYPE),
        budgets=AdmissionBudgets(max_archive_compression_ratio=2.0),
    )

    assert result.issues[0].code == "archive_budget_exceeded"
    assert result.evidence.node_count is None


def test_admission_detects_source_identity_changes(tmp_path: Path) -> None:
    source = _source(tmp_path, "paper.txt", b"first", "text/plain")
    source.filesystem_path.write_bytes(b"other")

    result = admit_source(source)

    assert result.issues[0].code == "source_changed"


def test_batch_admission_preserves_caller_order_and_one_policy(tmp_path: Path) -> None:
    first = _source(tmp_path, "b.txt", b"b", "text/plain")
    second = _source(tmp_path, "a.md", b"# a", "text/markdown")
    budgets = AdmissionBudgets(max_text_bytes=8)

    results = admit_sources((first, second), budgets=budgets)

    assert [result.source.relative_path for result in results] == ["b.txt", "a.md"]
    assert all(result.budgets is budgets for result in results)


def test_admission_budget_values_must_be_positive() -> None:
    with pytest.raises(ValueError, match="max_pages"):
        AdmissionBudgets(max_pages=0)
