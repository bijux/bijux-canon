# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical source metadata with lossless raw-value provenance."""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass
from typing import Literal, TypeAlias, get_args

from bijux_canon_ingest.domain.source_admission import SourceFormat

MetadataField = Literal[
    "doi",
    "canonical_uri",
    "authors",
    "publication_date",
    "title",
    "journal",
    "language",
    "license_expression",
    "license_url",
    "relative_path",
    "media_type",
]
MetadataValue: TypeAlias = str | tuple[str, ...]

_FIELDS = frozenset(get_args(MetadataField))
_FORMATS = frozenset(get_args(SourceFormat))


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _json_value(value: MetadataValue) -> str | list[str]:
    return list(value) if isinstance(value, tuple) else value


@dataclass(frozen=True, slots=True)
class RawMetadataValue:
    """One exact supplied value and the boundary that supplied it."""

    field: MetadataField
    value: MetadataValue
    provenance: str

    def __post_init__(self) -> None:
        if self.field not in _FIELDS:
            raise ValueError("unsupported metadata field")
        if not self.provenance:
            raise ValueError("RawMetadataValue.provenance must not be empty")
        if isinstance(self.value, tuple):
            if not self.value or any(
                not isinstance(item, str) or not item for item in self.value
            ):
                raise ValueError("metadata tuple values must contain non-empty strings")
        elif not isinstance(self.value, str) or not self.value:
            raise ValueError("metadata values must not be empty")

    def manifest(self) -> dict[str, object]:
        return {
            "field": self.field,
            "provenance": self.provenance,
            "value": _json_value(self.value),
        }


@dataclass(frozen=True, slots=True)
class MetadataConflict:
    """A canonical disagreement retained instead of silently overwriting identity."""

    field: MetadataField
    selected: RawMetadataValue
    alternatives: tuple[RawMetadataValue, ...]

    def __post_init__(self) -> None:
        if self.field != self.selected.field or any(
            alternative.field != self.field for alternative in self.alternatives
        ):
            raise ValueError("metadata conflict values must describe one field")
        if not self.alternatives:
            raise ValueError("metadata conflicts require at least one alternative")

    def manifest(self) -> dict[str, object]:
        return {
            "alternatives": [value.manifest() for value in self.alternatives],
            "field": self.field,
            "selected": self.selected.manifest(),
        }


@dataclass(frozen=True, slots=True)
class CanonicalSourceMetadata:
    """Normalized metadata bound to immutable source content and location."""

    source_content_sha256: str
    format_id: SourceFormat
    doi: str | None
    canonical_uri: str | None
    authors: tuple[str, ...]
    publication_date: str | None
    title: str | None
    journal: str | None
    language: str | None
    license_expression: str | None
    license_url: str | None
    relative_path: str
    media_type: str
    raw_values: tuple[RawMetadataValue, ...]
    conflicts: tuple[MetadataConflict, ...]

    def __post_init__(self) -> None:
        if len(self.source_content_sha256) != 64 or any(
            character not in "0123456789abcdef"
            for character in self.source_content_sha256
        ):
            raise ValueError("source metadata requires a lowercase SHA-256 digest")
        if self.format_id not in _FORMATS:
            raise ValueError("source metadata requires a supported format")
        if not self.relative_path or not self.media_type:
            raise ValueError("source metadata requires path and media type identity")
        raw_order = [(item.field, item.provenance) for item in self.raw_values]
        if raw_order != sorted(raw_order):
            raise ValueError("raw metadata values must use canonical order")
        conflict_fields = [conflict.field for conflict in self.conflicts]
        if conflict_fields != sorted(conflict_fields) or len(conflict_fields) != len(
            set(conflict_fields)
        ):
            raise ValueError(
                "metadata conflicts must be unique and canonically ordered"
            )

    def manifest(self) -> dict[str, object]:
        """Return the normalized values, lossless inputs, conflicts, and identity."""

        payload: dict[str, object] = {
            "authors": list(self.authors),
            "canonical_uri": self.canonical_uri,
            "conflicts": [conflict.manifest() for conflict in self.conflicts],
            "doi": self.doi,
            "format_id": self.format_id,
            "journal": self.journal,
            "language": self.language,
            "license_expression": self.license_expression,
            "license_url": self.license_url,
            "media_type": self.media_type,
            "publication_date": self.publication_date,
            "raw_values": [value.manifest() for value in self.raw_values],
            "relative_path": self.relative_path,
            "schema_version": "bijux.canon.ingest.source_metadata.v1",
            "source_content_sha256": self.source_content_sha256,
            "title": self.title,
        }
        return {"manifest_sha256": _identity(payload), **payload}


__all__ = [
    "CanonicalSourceMetadata",
    "MetadataConflict",
    "MetadataField",
    "MetadataValue",
    "RawMetadataValue",
]
