# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Compatibility wrapper for older CLI pipeline-shell imports."""

from __future__ import annotations

from bijux_canon_ingest.interfaces.cli.document_pipeline import DocumentChunkShell

IngestFileShell = DocumentChunkShell

__all__ = ["IngestFileShell"]
