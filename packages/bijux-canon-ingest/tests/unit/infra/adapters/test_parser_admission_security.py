# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Bounded parser-admission fuzzing with durable minimal regressions."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st

from bijux_canon_ingest import AdmissionBudgets, DiscoveredSource, admit_source

REPOSITORY_ROOT = Path(__file__).resolve().parents[6]
PORTFOLIO_ROOT = REPOSITORY_ROOT / "examples" / "document-formats"

PARSER_SHAPES = (
    ("fuzz.xml", "application/xml", b"<?xml version='1.0'?><article>", b"</article>"),
    ("fuzz.pdf", "application/pdf", b"%PDF-1.7\n", b"\nstartxref\n0\n%%EOF\n"),
    ("fuzz.html", "text/html", b"<!doctype html><html><body>", b"</body></html>"),
    (
        "fuzz.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK\x03\x04",
        b"",
    ),
    ("fuzz.md", "text/markdown", b"# Heading\n", b""),
    ("fuzz.txt", "text/plain", b"", b""),
)

MINIMAL_REPRODUCERS = (
    ("truncated.xml", "application/xml", b"<article>", "malformed_input"),
    (
        "entity.xml",
        "application/xml",
        b"<!DOCTYPE article [<!ENTITY x 'expanded'>]><article>&x;</article>",
        "unsafe_markup",
    ),
    ("truncated.pdf", "application/pdf", b"%PDF-1.7\n", "malformed_input"),
    (
        "invalid.html",
        "text/html",
        b"<!doctype html><html>\xff</html>",
        "malformed_input",
    ),
    (
        "truncated.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        b"PK\x03\x04broken",
        "malformed_input",
    ),
    ("invalid.md", "text/markdown", b"# heading\n\xff", "unsupported_input"),
    ("invalid.txt", "text/plain", b"text\xff", "unsupported_input"),
)


def _source(path: Path, content: bytes, media_type: str) -> DiscoveredSource:
    path.write_bytes(content)
    return DiscoveredSource.create(
        root_name="parser-security",
        relative_path=path.name,
        filesystem_path=path,
        content_sha256=hashlib.sha256(content).hexdigest(),
        byte_length=len(content),
        media_type=media_type,
        is_symlink=False,
    )


@pytest.mark.parametrize(("name", "media_type", "prefix", "suffix"), PARSER_SHAPES)
@settings(
    max_examples=64,
    derandomize=True,
    deadline=None,
    suppress_health_check=(HealthCheck.function_scoped_fixture,),
)
@given(payload=st.binary(max_size=2_048))
def test_parser_shaped_bytes_have_deterministic_bounded_outcomes(
    tmp_path: Path,
    name: str,
    media_type: str,
    prefix: bytes,
    suffix: bytes,
    payload: bytes,
) -> None:
    content = prefix + payload + suffix
    source = _source(tmp_path / name, content, media_type)
    budgets = AdmissionBudgets(
        max_file_bytes=4_096,
        max_archive_members=32,
        max_archive_member_bytes=4_096,
        max_archive_uncompressed_bytes=8_192,
        max_archive_compression_ratio=20.0,
        max_pages=32,
        max_nodes=256,
        max_text_bytes=4_096,
    )

    first = admit_source(source, budgets=budgets)
    second = admit_source(source, budgets=budgets)

    assert first.manifest() == second.manifest()
    if first.admitted:
        assert first.format_id is not None
        assert first.issues == ()
    else:
        assert first.format_id is None
        assert len(first.issues) == 1


@pytest.mark.parametrize(
    ("name", "media_type", "content", "expected_code"), MINIMAL_REPRODUCERS
)
def test_minimal_malformed_reproducers_fail_closed(
    tmp_path: Path,
    name: str,
    media_type: str,
    content: bytes,
    expected_code: str,
) -> None:
    result = admit_source(_source(tmp_path / name, content, media_type))

    assert result.admitted is False
    assert result.issues[0].code == expected_code


@pytest.mark.parametrize(
    ("name", "media_type", "content", "expected_code"),
    (
        (
            "deep.xml",
            "application/xml",
            b"<article>" + b"<n>" * 64 + b"x" + b"</n>" * 64 + b"</article>",
            "node_budget_exceeded",
        ),
        (
            "deep.html",
            "text/html",
            b"<!doctype html><html>" + b"<div>" * 64 + b"x" + b"</div>" * 64,
            "node_budget_exceeded",
        ),
        (
            "pages.pdf",
            "application/pdf",
            b"%PDF-1.7\n2 0 obj << /Type /Pages /Count 64 >> endobj\n"
            b"startxref\n0\n%%EOF\n",
            "page_budget_exceeded",
        ),
        ("large.md", "text/markdown", b"# " + b"x" * 64, "text_budget_exceeded"),
        ("large.txt", "text/plain", b"x" * 64, "text_budget_exceeded"),
    ),
)
def test_extreme_structure_stops_at_declared_resource_budgets(
    tmp_path: Path,
    name: str,
    media_type: str,
    content: bytes,
    expected_code: str,
) -> None:
    result = admit_source(
        _source(tmp_path / name, content, media_type),
        budgets=AdmissionBudgets(max_nodes=8, max_pages=8, max_text_bytes=8),
    )

    assert result.admitted is False
    assert result.issues[0].code == expected_code


def test_locked_real_parser_portfolio_remains_admitted_by_installed_surface() -> None:
    lock = json.loads((PORTFOLIO_ROOT / "corpus.lock.json").read_text())
    media_types = {
        "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        "html": "text/html",
        "jats": "application/xml",
        "markdown": "text/markdown",
        "pdf-digital": "application/pdf",
        "text": "text/plain",
    }
    parser_sources = tuple(
        record for record in lock["sources"] if record["format_id"] in media_types
    )

    assert len(parser_sources) == 6
    for record in parser_sources:
        path = PORTFOLIO_ROOT / record["local_path"]
        content = path.read_bytes()
        assert hashlib.sha256(content).hexdigest() == record["sha256"]
        result = admit_source(
            DiscoveredSource.create(
                root_name="parser-qualification",
                relative_path=path.name,
                filesystem_path=path,
                content_sha256=record["sha256"],
                byte_length=len(content),
                media_type=media_types[record["format_id"]],
                is_symlink=False,
            )
        )
        assert result.admitted is True, record["parser_source_id"]
        assert result.format_id == record["format_id"]
