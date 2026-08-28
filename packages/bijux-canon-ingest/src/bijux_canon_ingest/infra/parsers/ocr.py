# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Evidence-only OCR requirement classification without text recognition."""

from __future__ import annotations

import hashlib
from io import BytesIO

from pypdf import PdfReader

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    OcrRequiredOutcome,
    SourceLocator,
)


def _jpeg_dimensions(content: bytes) -> tuple[int, int]:
    position = 2
    frame_markers = frozenset(
        {*range(0xC0, 0xC4), *range(0xC5, 0xC8), *range(0xC9, 0xCC), *range(0xCD, 0xD0)}
    )
    while position + 8 < len(content):
        if content[position] != 0xFF:
            position += 1
            continue
        while position < len(content) and content[position] == 0xFF:
            position += 1
        marker = content[position]
        position += 1
        if marker in frame_markers:
            height = int.from_bytes(content[position + 3 : position + 5], "big")
            width = int.from_bytes(content[position + 5 : position + 7], "big")
            return width, height
        if marker in {0x00, 0x01, 0xD8, 0xD9, *range(0xD0, 0xD8)}:
            continue
        length = int.from_bytes(content[position : position + 2], "big")
        position += length
    raise DocumentParseError("malformed_document", "JPEG dimensions cannot be resolved")


def image_ocr_requirement(
    content: bytes, *, source_content_sha256: str, media_type: str
) -> OcrRequiredOutcome:
    """Return whole-image OCR evidence for an admitted image."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "image bytes changed after admission"
        )
    if media_type == "image/jpeg":
        width, height = _jpeg_dimensions(content)
    elif media_type == "image/png":
        width = int.from_bytes(content[16:20], "big")
        height = int.from_bytes(content[20:24], "big")
    elif media_type == "image/gif":
        width = int.from_bytes(content[6:8], "little")
        height = int.from_bytes(content[8:10], "little")
    elif media_type == "image/bmp":
        width = abs(int.from_bytes(content[18:22], "little", signed=True))
        height = abs(int.from_bytes(content[22:26], "little", signed=True))
    else:
        raise DocumentParseError(
            "ocr_required", f"{media_type} requires OCR; dimensions are not exposed"
        )
    return OcrRequiredOutcome(
        source_content_sha256=source_content_sha256,
        media_type=media_type,
        reason="image contains no embedded text and requires OCR",
        locator=SourceLocator(
            scheme="image-region",
            selectors=(
                ("x", 0),
                ("y", 0),
                ("width", width),
                ("height", height),
                ("unit", "pixel"),
            ),
        ),
    )


def pdf_ocr_requirement(
    content: bytes, *, source_content_sha256: str
) -> OcrRequiredOutcome:
    """Return page evidence only when every PDF page lacks digital text."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError("source_changed", "PDF bytes changed after admission")
    try:
        reader = PdfReader(BytesIO(content), strict=True)
        pages = list(reader.pages)
        if not pages or any((page.extract_text() or "").strip() for page in pages):
            raise DocumentParseError(
                "format_mismatch", "PDF has digital text and does not require OCR"
            )
    except DocumentParseError:
        raise
    except Exception as error:
        raise DocumentParseError(
            "malformed_document", "PDF cannot be inspected"
        ) from error
    return OcrRequiredOutcome(
        source_content_sha256=source_content_sha256,
        media_type="application/pdf",
        reason="all PDF pages lack extractable digital text and require OCR",
        page_count=len(pages),
        locator=SourceLocator(
            scheme="pdf-page-range",
            selectors=(("page_start", 1), ("page_end", len(pages))),
        ),
    )


__all__ = ["image_ocr_requirement", "pdf_ocr_requirement"]
