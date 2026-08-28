# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed policy and outcomes for source admission before parser expansion."""

from __future__ import annotations

import hashlib
import json
import math
import re
from dataclasses import dataclass
from typing import Literal, get_args

from bijux_canon_ingest.domain.source_discovery import DiscoveredSource

SourceFormat = Literal[
    "jats",
    "pdf-digital",
    "html",
    "markdown",
    "text",
    "docx",
    "ocr-required",
]
AdmissionDisposition = Literal["admitted", "rejected"]
AdmissionIssueCode = Literal[
    "archive_budget_exceeded",
    "encrypted_input",
    "file_budget_exceeded",
    "malformed_input",
    "media_type_mismatch",
    "node_budget_exceeded",
    "page_budget_exceeded",
    "source_changed",
    "text_budget_exceeded",
    "unsafe_archive",
    "unsafe_markup",
    "unsupported_input",
]

_DISPOSITIONS: frozenset[str] = frozenset(get_args(AdmissionDisposition))
_FORMATS: frozenset[str] = frozenset(get_args(SourceFormat))
_ISSUE_CODES: frozenset[str] = frozenset(get_args(AdmissionIssueCode))
_MEDIA_TYPE = re.compile(r"^[!#$%&'*+.^_`|~0-9a-z-]+/[!#$%&'*+.^_`|~0-9a-z-]+$")


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def normalize_media_type(value: str) -> str:
    """Return a lowercase MIME essence without parameters."""

    essence = value.partition(";")[0].strip().lower()
    if _MEDIA_TYPE.fullmatch(essence) is None:
        raise ValueError("media type must contain one non-empty type/subtype essence")
    return essence


@dataclass(frozen=True, slots=True)
class AdmissionBudgets:
    """Finite limits applied before a source can reach a format parser."""

    max_file_bytes: int = 64 * 1024 * 1024
    max_archive_members: int = 2_048
    max_archive_member_bytes: int = 32 * 1024 * 1024
    max_archive_uncompressed_bytes: int = 128 * 1024 * 1024
    max_archive_compression_ratio: float = 100.0
    max_pages: int = 2_000
    max_nodes: int = 2_000_000
    max_text_bytes: int = 64 * 1024 * 1024

    def __post_init__(self) -> None:
        integer_values = {
            "max_file_bytes": self.max_file_bytes,
            "max_archive_members": self.max_archive_members,
            "max_archive_member_bytes": self.max_archive_member_bytes,
            "max_archive_uncompressed_bytes": self.max_archive_uncompressed_bytes,
            "max_pages": self.max_pages,
            "max_nodes": self.max_nodes,
            "max_text_bytes": self.max_text_bytes,
        }
        for name, value in integer_values.items():
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                raise ValueError(f"AdmissionBudgets.{name} must be positive")
        ratio = self.max_archive_compression_ratio
        if (
            isinstance(ratio, bool)
            or not isinstance(ratio, int | float)
            or not math.isfinite(ratio)
            or ratio <= 0
        ):
            raise ValueError(
                "AdmissionBudgets.max_archive_compression_ratio must be positive and finite"
            )

    def identity_payload(self) -> dict[str, int | float]:
        """Return all policy limits in stable field order."""

        return {
            "max_archive_compression_ratio": self.max_archive_compression_ratio,
            "max_archive_member_bytes": self.max_archive_member_bytes,
            "max_archive_members": self.max_archive_members,
            "max_archive_uncompressed_bytes": self.max_archive_uncompressed_bytes,
            "max_file_bytes": self.max_file_bytes,
            "max_nodes": self.max_nodes,
            "max_pages": self.max_pages,
            "max_text_bytes": self.max_text_bytes,
        }


@dataclass(frozen=True, slots=True)
class AdmissionIssue:
    """One stable reason that a source was rejected at the admission boundary."""

    code: AdmissionIssueCode
    detail: str

    def __post_init__(self) -> None:
        if self.code not in _ISSUE_CODES:
            raise ValueError("unsupported admission issue code")
        if not self.detail:
            raise ValueError("AdmissionIssue.detail must not be empty")

    def identity_payload(self) -> dict[str, str]:
        return {"code": self.code, "detail": self.detail}


@dataclass(frozen=True, slots=True)
class AdmissionEvidence:
    """Bounded observations made without invoking a format parser."""

    byte_length: int
    declared_media_type: str
    detected_media_type: str | None
    archive_member_count: int | None = None
    archive_uncompressed_bytes: int | None = None
    node_count: int | None = None
    page_count: int | None = None
    text_bytes: int | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "declared_media_type",
            normalize_media_type(self.declared_media_type),
        )
        if self.detected_media_type is not None:
            object.__setattr__(
                self,
                "detected_media_type",
                normalize_media_type(self.detected_media_type),
            )
        for field_name in (
            "byte_length",
            "archive_member_count",
            "archive_uncompressed_bytes",
            "node_count",
            "page_count",
            "text_bytes",
        ):
            value = getattr(self, field_name)
            if value is not None and value < 0:
                raise ValueError(f"AdmissionEvidence.{field_name} must not be negative")

    def identity_payload(self) -> dict[str, int | str | None]:
        return {
            "archive_member_count": self.archive_member_count,
            "archive_uncompressed_bytes": self.archive_uncompressed_bytes,
            "byte_length": self.byte_length,
            "declared_media_type": self.declared_media_type,
            "detected_media_type": self.detected_media_type,
            "node_count": self.node_count,
            "page_count": self.page_count,
            "text_bytes": self.text_bytes,
        }


@dataclass(frozen=True, slots=True)
class AdmissionResult:
    """An immutable admitted format or typed rejection for one source identity."""

    source: DiscoveredSource
    budgets: AdmissionBudgets
    disposition: AdmissionDisposition
    format_id: SourceFormat | None
    evidence: AdmissionEvidence
    issues: tuple[AdmissionIssue, ...] = ()

    def __post_init__(self) -> None:
        if self.disposition not in _DISPOSITIONS:
            raise ValueError("unsupported admission disposition")
        if self.format_id is not None and self.format_id not in _FORMATS:
            raise ValueError("unsupported source format")
        if self.disposition == "admitted" and (self.format_id is None or self.issues):
            raise ValueError("admitted results require a format and no issues")
        if self.disposition == "rejected" and (
            self.format_id is not None or not self.issues
        ):
            raise ValueError("rejected results require issues and no format")

    @property
    def admitted(self) -> bool:
        """Whether the source may proceed to its identified format boundary."""

        return self.disposition == "admitted"

    def manifest(self) -> dict[str, object]:
        """Return a canonical result bound to source identity and admission policy."""

        payload: dict[str, object] = {
            "budgets": self.budgets.identity_payload(),
            "disposition": self.disposition,
            "evidence": self.evidence.identity_payload(),
            "format_id": self.format_id,
            "issues": [issue.identity_payload() for issue in self.issues],
            "schema_version": "bijux.canon.ingest.admission.v1",
            "source": {
                "content_sha256": self.source.content_sha256,
                "location_id": self.source.location_id,
            },
        }
        return {"manifest_sha256": _sha256_identity(payload), **payload}


__all__ = [
    "AdmissionBudgets",
    "AdmissionDisposition",
    "AdmissionEvidence",
    "AdmissionIssue",
    "AdmissionIssueCode",
    "AdmissionResult",
    "SourceFormat",
    "normalize_media_type",
]
