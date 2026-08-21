# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Filesystem adapter coordinating source identity and format admission."""

from __future__ import annotations

import hashlib
import os
import re
import stat
from dataclasses import dataclass

from bijux_canon_ingest.domain.source_admission import (
    AdmissionBudgets,
    AdmissionEvidence,
    AdmissionIssue,
    AdmissionIssueCode,
    AdmissionResult,
    SourceFormat,
    normalize_media_type,
)
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource
from bijux_canon_ingest.infra.admission.docx import DOCX_MEDIA_TYPE, inspect_docx
from bijux_canon_ingest.infra.admission.images import (
    identify_image_media_type,
    inspect_image,
)
from bijux_canon_ingest.infra.admission.limits import AdmissionFailure
from bijux_canon_ingest.infra.admission.markup import (
    inspect_html,
    inspect_text,
    inspect_xml,
)
from bijux_canon_ingest.infra.admission.pdf import PDF_HEADER, inspect_pdf

_READ_SIZE = 1024 * 1024
_XML_MEDIA_TYPES = frozenset({"application/xml", "application/jats+xml"})


@dataclass(slots=True)
class _Observations:
    detected_media_type: str | None = None
    archive_member_count: int | None = None
    archive_uncompressed_bytes: int | None = None
    node_count: int | None = None
    page_count: int | None = None
    text_bytes: int | None = None


def _evidence(
    source: DiscoveredSource,
    declared_media_type: str,
    observations: _Observations,
) -> AdmissionEvidence:
    return AdmissionEvidence(
        byte_length=source.byte_length,
        declared_media_type=declared_media_type,
        detected_media_type=observations.detected_media_type,
        archive_member_count=observations.archive_member_count,
        archive_uncompressed_bytes=observations.archive_uncompressed_bytes,
        node_count=observations.node_count,
        page_count=observations.page_count,
        text_bytes=observations.text_bytes,
    )


def _reject(
    source: DiscoveredSource,
    budgets: AdmissionBudgets,
    declared_media_type: str,
    observations: _Observations,
    code: AdmissionIssueCode,
    detail: str,
) -> AdmissionResult:
    return AdmissionResult(
        source=source,
        budgets=budgets,
        disposition="rejected",
        format_id=None,
        evidence=_evidence(source, declared_media_type, observations),
        issues=(AdmissionIssue(code, detail),),
    )


def _read_current_source(
    source: DiscoveredSource,
    budgets: AdmissionBudgets,
) -> bytes:
    try:
        current_stat = source.filesystem_path.stat()
    except OSError as error:
        raise AdmissionFailure(
            "source_changed", "source is no longer readable"
        ) from error
    if not stat.S_ISREG(current_stat.st_mode):
        raise AdmissionFailure("source_changed", "source is no longer a regular file")
    if current_stat.st_size != source.byte_length:
        raise AdmissionFailure(
            "source_changed", "source byte length changed after discovery"
        )
    if current_stat.st_size > budgets.max_file_bytes:
        raise AdmissionFailure(
            "file_budget_exceeded",
            f"source exceeds max_file_bytes={budgets.max_file_bytes}",
        )

    content = bytearray()
    digest = hashlib.sha256()
    try:
        with source.filesystem_path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            while chunk := handle.read(_READ_SIZE):
                if len(content) + len(chunk) > budgets.max_file_bytes:
                    raise AdmissionFailure(
                        "file_budget_exceeded",
                        f"source exceeds max_file_bytes={budgets.max_file_bytes}",
                    )
                content.extend(chunk)
                digest.update(chunk)
            after = os.fstat(handle.fileno())
    except AdmissionFailure:
        raise
    except OSError as error:
        raise AdmissionFailure(
            "source_changed", "source could not be read completely"
        ) from error

    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(getattr(before, name) != getattr(after, name) for name in stable_fields):
        raise AdmissionFailure("source_changed", "source changed during admission")
    if (
        after.st_size != source.byte_length
        or digest.hexdigest() != source.content_sha256
    ):
        raise AdmissionFailure(
            "source_changed", "source content identity changed after discovery"
        )
    return bytes(content)


def _initial_media_type(content: bytes, declared: str) -> str | None:
    prefix = content[:1024]
    stripped = content.lstrip(b"\xef\xbb\xbf\x00\t\n\r ")
    lowered = stripped[:1024].lower()
    pdf_match = PDF_HEADER.search(prefix)
    if pdf_match is not None and pdf_match.start() <= 1020:
        return "application/pdf"
    if content.startswith((b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08")):
        return "application/zip"
    image_media_type = identify_image_media_type(content)
    if image_media_type is not None:
        return image_media_type
    if lowered.startswith(b"<!doctype html") or re.search(rb"<html(?:\s|>)", lowered):
        return "text/html"
    if lowered.startswith((b"<?xml", b"<article")):
        return "application/xml"
    if declared in _XML_MEDIA_TYPES and stripped.startswith(b"<"):
        return "application/xml"
    try:
        content.decode("utf-8-sig")
    except UnicodeDecodeError:
        return None
    if b"\x00" in content:
        return None
    return "text/plain"


def _media_types_compatible(
    declared: str,
    detected: str,
    format_id: SourceFormat,
) -> bool:
    if format_id == "jats":
        return declared in _XML_MEDIA_TYPES
    if format_id == "markdown":
        return declared == "text/markdown" and detected == "text/plain"
    if format_id == "text":
        return declared == "text/plain" and detected == "text/plain"
    if format_id == "ocr-required":
        return declared == detected or declared == "image/*"
    return declared == detected


def _inspect_supported_format(
    content: bytes,
    declared: str,
    budgets: AdmissionBudgets,
    observations: _Observations,
) -> SourceFormat:
    detected = _initial_media_type(content, declared)
    observations.detected_media_type = detected
    if detected is None:
        raise AdmissionFailure(
            "unsupported_input", "source bytes do not identify an admitted format"
        )

    format_id: SourceFormat
    if detected == "application/pdf":
        observations.page_count = inspect_pdf(content, budgets)
        format_id = "pdf-digital"
    elif detected == "application/zip":
        if declared != DOCX_MEDIA_TYPE:
            raise AdmissionFailure(
                "unsupported_input", "ZIP input is supported only as a DOCX package"
            )
        inspection = inspect_docx(content, budgets)
        observations.archive_member_count = inspection.archive_member_count
        observations.archive_uncompressed_bytes = inspection.archive_uncompressed_bytes
        observations.node_count = inspection.node_count
        observations.text_bytes = inspection.text_bytes
        observations.detected_media_type = DOCX_MEDIA_TYPE
        detected = DOCX_MEDIA_TYPE
        format_id = "docx"
    elif detected == "application/xml":
        root_name, node_count, text_bytes = inspect_xml(content, budgets)
        observations.node_count = node_count
        observations.text_bytes = text_bytes
        if root_name != "article":
            raise AdmissionFailure(
                "unsupported_input", "XML input is not a JATS article document"
            )
        observations.detected_media_type = "application/jats+xml"
        detected = "application/jats+xml"
        format_id = "jats"
    elif detected == "text/html":
        observations.node_count, observations.text_bytes = inspect_html(
            content, budgets
        )
        format_id = "html"
    elif detected == "text/plain":
        observations.text_bytes = inspect_text(content, budgets)
        format_id = "markdown" if declared == "text/markdown" else "text"
    elif detected.startswith("image/"):
        inspect_image(content, detected)
        format_id = "ocr-required"
    else:
        raise AdmissionFailure(
            "unsupported_input", "source bytes do not identify an admitted format"
        )

    if not _media_types_compatible(declared, detected, format_id):
        raise AdmissionFailure(
            "media_type_mismatch",
            f"declared media type {declared} conflicts with detected {detected}",
        )
    return format_id


def admit_filesystem_source(
    source: DiscoveredSource,
    *,
    declared_media_type: str | None = None,
    budgets: AdmissionBudgets | None = None,
) -> AdmissionResult:
    """Revalidate and preflight one discovered source under finite budgets."""

    policy = budgets if budgets is not None else AdmissionBudgets()
    declared = normalize_media_type(
        source.media_type if declared_media_type is None else declared_media_type
    )
    observations = _Observations()
    try:
        content = _read_current_source(source, policy)
        format_id = _inspect_supported_format(content, declared, policy, observations)
    except AdmissionFailure as failure:
        return _reject(
            source,
            policy,
            declared,
            observations,
            failure.code,
            failure.detail,
        )
    return AdmissionResult(
        source=source,
        budgets=policy,
        disposition="admitted",
        format_id=format_id,
        evidence=_evidence(source, declared, observations),
    )


__all__ = ["admit_filesystem_source"]
