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
MetadataSource = Literal[
    "source_discovery",
    "user_override",
    "corpus_lock",
    "acquisition_receipt",
    "embedded_parser",
    "filename_fallback",
]
METADATA_SOURCE_PRECEDENCE: tuple[MetadataSource, ...] = (
    "source_discovery",
    "user_override",
    "corpus_lock",
    "acquisition_receipt",
    "embedded_parser",
    "filename_fallback",
)

_FIELDS = frozenset(get_args(MetadataField))
_FORMATS = frozenset(get_args(SourceFormat))
_SOURCES = frozenset(get_args(MetadataSource))
_SOURCE_PRECEDENCE = {
    source: rank for rank, source in enumerate(METADATA_SOURCE_PRECEDENCE)
}


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


def _valid_identity(value: str) -> bool:
    return (
        value.startswith("sha256:")
        and len(value) == 71
        and all(character in "0123456789abcdef" for character in value[7:])
    )


@dataclass(frozen=True, slots=True)
class RawMetadataValue:
    """One exact input, its normalized value, and its immutable provenance."""

    field: MetadataField
    value: MetadataValue
    normalized_value: MetadataValue
    source: MetadataSource
    provenance: str
    provenance_sha256: str

    def __post_init__(self) -> None:
        if self.field not in _FIELDS:
            raise ValueError("unsupported metadata field")
        if not self.provenance:
            raise ValueError("RawMetadataValue.provenance must not be empty")
        if self.source not in _SOURCES:
            raise ValueError("unsupported metadata source")
        if not _valid_identity(self.provenance_sha256):
            raise ValueError("metadata provenance requires a SHA-256 identity")
        for value in (self.value, self.normalized_value):
            if isinstance(value, tuple):
                if not value or any(
                    not isinstance(item, str) or not item for item in value
                ):
                    raise ValueError(
                        "metadata tuple values must contain non-empty strings"
                    )
            elif not isinstance(value, str) or not value:
                raise ValueError("metadata values must not be empty")

    def manifest(self) -> dict[str, object]:
        return {
            "field": self.field,
            "normalized_value": _json_value(self.normalized_value),
            "provenance": self.provenance,
            "provenance_sha256": self.provenance_sha256,
            "source": self.source,
            "value": _json_value(self.value),
        }


@dataclass(frozen=True, slots=True)
class MetadataProvenanceRecord:
    """Identity evidence for one complete metadata input record."""

    source: MetadataSource
    provenance: str
    provenance_sha256: str
    format_id: SourceFormat | None
    source_content_sha256: str | None
    source_byte_length: int | None
    fields: tuple[MetadataField, ...]

    def __post_init__(self) -> None:
        if self.source not in _SOURCES or not self.provenance:
            raise ValueError(
                "metadata provenance record requires source and provenance"
            )
        if not _valid_identity(self.provenance_sha256):
            raise ValueError("metadata provenance record requires a SHA-256 identity")
        if self.format_id is not None and self.format_id not in _FORMATS:
            raise ValueError("metadata provenance record format is unsupported")
        if self.source_content_sha256 is not None and (
            len(self.source_content_sha256) != 64
            or any(
                character not in "0123456789abcdef"
                for character in self.source_content_sha256
            )
        ):
            raise ValueError("metadata source content digest must be lowercase SHA-256")
        if self.source_byte_length is not None and (
            not isinstance(self.source_byte_length, int)
            or isinstance(self.source_byte_length, bool)
            or self.source_byte_length < 0
        ):
            raise ValueError("metadata source byte length must be non-negative")
        if self.fields != tuple(sorted(set(self.fields))):
            raise ValueError("metadata provenance fields must be unique and ordered")

    def manifest(self) -> dict[str, object]:
        return {
            "fields": list(self.fields),
            "format_id": self.format_id,
            "provenance": self.provenance,
            "provenance_sha256": self.provenance_sha256,
            "source": self.source,
            "source_content_sha256": self.source_content_sha256,
            "source_byte_length": self.source_byte_length,
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
    provenance_records: tuple[MetadataProvenanceRecord, ...]
    selected_values: tuple[RawMetadataValue, ...]
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
        raw_order = [
            (
                item.field,
                _SOURCE_PRECEDENCE[item.source],
                item.provenance,
                item.provenance_sha256,
            )
            for item in self.raw_values
        ]
        if raw_order != sorted(raw_order):
            raise ValueError("raw metadata values must use canonical order")
        provenance_order = [
            (
                _SOURCE_PRECEDENCE[item.source],
                item.provenance,
                item.provenance_sha256,
            )
            for item in self.provenance_records
        ]
        if provenance_order != sorted(provenance_order):
            raise ValueError("metadata provenance records must use canonical order")
        selected_fields = [item.field for item in self.selected_values]
        if selected_fields != sorted(selected_fields) or len(selected_fields) != len(
            set(selected_fields)
        ):
            raise ValueError("selected metadata values must be unique and ordered")
        if any(item not in self.raw_values for item in self.selected_values):
            raise ValueError("selected metadata values must retain their raw input")
        provenance_identities = {
            (item.source, item.provenance, item.provenance_sha256)
            for item in self.provenance_records
        }
        if any(
            (item.source, item.provenance, item.provenance_sha256)
            not in provenance_identities
            for item in self.raw_values
        ):
            raise ValueError("raw metadata values require a retained provenance record")
        conflict_fields = [conflict.field for conflict in self.conflicts]
        if conflict_fields != sorted(conflict_fields) or len(conflict_fields) != len(
            set(conflict_fields)
        ):
            raise ValueError(
                "metadata conflicts must be unique and canonically ordered"
            )
        if any(
            conflict.selected not in self.selected_values
            or any(value not in self.raw_values for value in conflict.alternatives)
            for conflict in self.conflicts
        ):
            raise ValueError(
                "metadata conflicts must reference retained resolution data"
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
            "provenance_records": [
                record.manifest() for record in self.provenance_records
            ],
            "raw_values": [value.manifest() for value in self.raw_values],
            "relative_path": self.relative_path,
            "schema_version": "bijux.canon.ingest.source_metadata.v2",
            "selected_values": [value.manifest() for value in self.selected_values],
            "source_content_sha256": self.source_content_sha256,
            "title": self.title,
        }
        return {"manifest_sha256": _identity(payload), **payload}


__all__ = [
    "CanonicalSourceMetadata",
    "METADATA_SOURCE_PRECEDENCE",
    "MetadataConflict",
    "MetadataField",
    "MetadataProvenanceRecord",
    "MetadataSource",
    "MetadataValue",
    "RawMetadataValue",
]
