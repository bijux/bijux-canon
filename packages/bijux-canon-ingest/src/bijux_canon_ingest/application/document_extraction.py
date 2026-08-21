# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Application boundary for semantic extraction from admitted documents."""

from __future__ import annotations

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    ParsedDocument,
)
from bijux_canon_ingest.domain.source_admission import AdmissionResult
from bijux_canon_ingest.infra.adapters.file_admission import read_current_source
from bijux_canon_ingest.infra.admission.limits import AdmissionFailure
from bijux_canon_ingest.infra.parsers.jats import parse_jats_content


def parse_jats(admission: AdmissionResult) -> ParsedDocument:
    """Parse one immutable source admitted specifically as JATS."""

    if not admission.admitted:
        raise DocumentParseError(
            "source_not_admitted", "source must pass admission before JATS parsing"
        )
    if admission.format_id != "jats":
        raise DocumentParseError(
            "format_mismatch", "admitted source format is not JATS"
        )
    try:
        content = read_current_source(admission.source, admission.budgets)
    except AdmissionFailure as error:
        if error.code == "source_changed":
            raise DocumentParseError("source_changed", error.detail) from error
        raise DocumentParseError("unsafe_markup", error.detail) from error
    return parse_jats_content(
        content,
        source_content_sha256=admission.source.content_sha256,
    )


__all__ = ["parse_jats"]
