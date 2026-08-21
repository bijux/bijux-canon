# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Bounded PDF container, encryption, and page-count preflight."""

from __future__ import annotations

import re

from bijux_canon_ingest.domain.source_admission import AdmissionBudgets
from bijux_canon_ingest.infra.admission.limits import (
    AdmissionFailure,
    enforce_count,
)

PDF_HEADER = re.compile(rb"%PDF-[12]\.[0-9]")
_PDF_PAGE = re.compile(rb"/Type\s*/Page(?!s)\b")
_PDF_COUNT = re.compile(rb"/Count\s+([0-9]+)\b")


def inspect_pdf(content: bytes, budgets: AdmissionBudgets) -> int:
    """Establish a conservative page count and reject encrypted PDFs."""

    if PDF_HEADER.search(content[:1024]) is None:
        raise AdmissionFailure("malformed_input", "PDF header is missing")
    if b"%%EOF" not in content[-4096:] or b"startxref" not in content[-8192:]:
        raise AdmissionFailure("malformed_input", "PDF trailer is incomplete")
    if re.search(rb"/Encrypt\b", content) is not None:
        raise AdmissionFailure("encrypted_input", "encrypted PDF input is forbidden")
    explicit_pages = len(_PDF_PAGE.findall(content))
    declared_counts = [int(value) for value in _PDF_COUNT.findall(content)]
    page_count = max([explicit_pages, *declared_counts], default=0)
    if page_count == 0:
        raise AdmissionFailure(
            "malformed_input", "PDF page count cannot be established before parsing"
        )
    enforce_count(
        page_count,
        budgets.max_pages,
        "page_budget_exceeded",
        "max_pages",
    )
    return page_count


__all__ = ["PDF_HEADER", "inspect_pdf"]
