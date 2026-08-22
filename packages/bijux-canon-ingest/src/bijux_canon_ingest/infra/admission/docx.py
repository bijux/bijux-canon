# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""ZIP safety and bounded package-part preflight for DOCX sources."""

from __future__ import annotations

from dataclasses import dataclass
import io
from pathlib import PurePosixPath
import stat
import zipfile

from bijux_canon_ingest.domain.source_admission import AdmissionBudgets
from bijux_canon_ingest.infra.admission.limits import (
    AdmissionFailure,
    enforce_count,
)
from bijux_canon_ingest.infra.admission.markup import inspect_xml

DOCX_MEDIA_TYPE = (
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
)
_DOCUMENT_MEDIA_TYPE = (
    b"application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"
)
_COMPRESSION_METHODS = frozenset({zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED})


@dataclass(frozen=True, slots=True)
class DocxInspection:
    """Resource observations established before the DOCX parser boundary."""

    archive_member_count: int
    archive_uncompressed_bytes: int
    node_count: int
    text_bytes: int


def _validate_archive_path(name: str) -> None:
    if not name or "\\" in name or name.startswith("/"):
        raise AdmissionFailure(
            "unsafe_archive", "archive member path is not a portable relative path"
        )
    components = name.split("/")
    if components[-1] == "":
        components = components[:-1]
    if (
        not components
        or any(component in {"", ".", ".."} for component in components)
        or ":" in components[0]
        or PurePosixPath(name).is_absolute()
    ):
        raise AdmissionFailure(
            "unsafe_archive", "archive member path is not a portable relative path"
        )


def _inspect_members(
    members: list[zipfile.ZipInfo],
    budgets: AdmissionBudgets,
) -> tuple[set[str], int]:
    enforce_count(
        len(members),
        budgets.max_archive_members,
        "archive_budget_exceeded",
        "max_archive_members",
    )
    seen_names: set[str] = set()
    total_uncompressed = 0
    total_compressed = 0
    for member in members:
        _validate_archive_path(member.filename)
        if member.filename in seen_names:
            raise AdmissionFailure(
                "unsafe_archive", "archive contains duplicate member paths"
            )
        seen_names.add(member.filename)
        if member.flag_bits & 0x1:
            raise AdmissionFailure(
                "encrypted_input", "encrypted archive members are forbidden"
            )
        unix_mode = (member.external_attr >> 16) & 0o170000
        if unix_mode == stat.S_IFLNK:
            raise AdmissionFailure(
                "unsafe_archive", "archive symlink members are forbidden"
            )
        if member.compress_type not in _COMPRESSION_METHODS:
            raise AdmissionFailure(
                "unsafe_archive", "archive compression method is not admitted"
            )
        enforce_count(
            member.file_size,
            budgets.max_archive_member_bytes,
            "archive_budget_exceeded",
            "max_archive_member_bytes",
        )
        ratio = member.file_size / max(member.compress_size, 1)
        if ratio > budgets.max_archive_compression_ratio:
            raise AdmissionFailure(
                "archive_budget_exceeded",
                "archive member exceeds max_archive_compression_ratio="
                f"{budgets.max_archive_compression_ratio}",
            )
        total_uncompressed += member.file_size
        total_compressed += member.compress_size
        enforce_count(
            total_uncompressed,
            budgets.max_archive_uncompressed_bytes,
            "archive_budget_exceeded",
            "max_archive_uncompressed_bytes",
        )
    if total_uncompressed / max(total_compressed, 1) > (
        budgets.max_archive_compression_ratio
    ):
        raise AdmissionFailure(
            "archive_budget_exceeded",
            "archive exceeds max_archive_compression_ratio="
            f"{budgets.max_archive_compression_ratio}",
        )
    return seen_names, total_uncompressed


def inspect_docx(content: bytes, budgets: AdmissionBudgets) -> DocxInspection:
    """Validate ZIP metadata before bounded DOCX package-part decompression."""

    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise AdmissionFailure(
            "malformed_input", "DOCX ZIP container is malformed"
        ) from error

    with archive:
        members = archive.infolist()
        seen_names, total_uncompressed = _inspect_members(members, budgets)
        required_parts = {"[Content_Types].xml", "word/document.xml"}
        if not required_parts.issubset(seen_names):
            raise AdmissionFailure(
                "malformed_input", "DOCX container is missing required package parts"
            )
        try:
            content_types = archive.read("[Content_Types].xml")
            document = archive.read("word/document.xml")
        except (EOFError, RuntimeError, zipfile.BadZipFile, OSError) as error:
            raise AdmissionFailure(
                "malformed_input", "DOCX package parts failed integrity checks"
            ) from error

    types_root, types_nodes, types_text = inspect_xml(content_types, budgets)
    document_root, document_nodes, document_text = inspect_xml(document, budgets)
    if types_root != "Types" or document_root != "document":
        raise AdmissionFailure(
            "malformed_input", "DOCX package parts have unexpected root elements"
        )
    if _DOCUMENT_MEDIA_TYPE not in content_types:
        raise AdmissionFailure(
            "malformed_input", "DOCX content types do not declare a document part"
        )
    node_count = types_nodes + document_nodes
    text_bytes = types_text + document_text
    enforce_count(
        node_count,
        budgets.max_nodes,
        "node_budget_exceeded",
        "max_nodes",
    )
    enforce_count(
        text_bytes,
        budgets.max_text_bytes,
        "text_budget_exceeded",
        "max_text_bytes",
    )
    return DocxInspection(
        archive_member_count=len(members),
        archive_uncompressed_bytes=total_uncompressed,
        node_count=node_count,
        text_bytes=text_bytes,
    )


__all__ = ["DOCX_MEDIA_TYPE", "DocxInspection", "inspect_docx"]
