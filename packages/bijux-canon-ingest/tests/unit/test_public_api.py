# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import bijux_canon_ingest as ingest


def test_root_package_exports_version() -> None:
    assert "__version__" in ingest.__all__
    assert isinstance(ingest.__version__, str)
    assert ingest.__version__


def test_root_package_declares_lazy_exports_in_dir() -> None:
    exported_names = dir(ingest)
    assert "DiscoveryPolicy" in exported_names
    assert "IngestConfig" in exported_names
    assert "build_ingest_deps" in exported_names
    assert "assess_ocr_requirement" in exported_names
    assert "discover_sources" in exported_names
    assert "parse_docx" in exported_names
    assert "parse_html" in exported_names
    assert "parse_jats" in exported_names
    assert "parse_markdown" in exported_names
    assert "parse_pdf" in exported_names
    assert "parse_text" in exported_names
    assert "normalize_source_metadata" in exported_names
    assert "build_chunk_span_mapping" in exported_names
    assert "build_document_span_mappings" in exported_names
    assert "chunk_document_mappings" in exported_names
    assert "build_corpus_snapshot" in exported_names
