# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility wrapper for older CLI file helper imports."""

from __future__ import annotations

from bijux_canon_ingest.interfaces.cli.document_io import (
    CsvDocumentReader,
    DocumentChunkApi,
    read_docs_csv,
    run,
    write_chunks_jsonl,
)

FSReader = CsvDocumentReader
IngestApiShell = DocumentChunkApi

__all__ = [
    "FSReader",
    "IngestApiShell",
    "read_docs_csv",
    "run",
    "write_chunks_jsonl",
]
