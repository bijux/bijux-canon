# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Normalization service for source and extracted metadata records."""

from __future__ import annotations

import hashlib
import json
import re
import unicodedata
from collections.abc import Iterable, Mapping, Sequence
from contextlib import suppress
from dataclasses import dataclass
from datetime import date, datetime
from pathlib import PurePosixPath
from typing import Literal, cast, get_args
from urllib.parse import SplitResult, urlsplit, urlunsplit

from bijux_canon_ingest.domain.source_admission import (
    SourceFormat,
    normalize_media_type,
)
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource
from bijux_canon_ingest.domain.source_metadata import (
    METADATA_SOURCE_PRECEDENCE,
    CanonicalSourceMetadata,
    MetadataConflict,
    MetadataField,
    MetadataProvenanceRecord,
    MetadataSource,
    MetadataValue,
    RawMetadataValue,
)

_DOI = re.compile(r"^10\.\d{4,9}/\S+$", re.IGNORECASE)
_PDF_DATE = re.compile(r"^D:(\d{4})(\d{2})?(\d{2})?")
_SPDX_NAMES = {
    "apache-2.0": "Apache-2.0",
    "cc-by-4.0": "CC-BY-4.0",
    "cc0-1.0": "CC0-1.0",
    "ietf-trust-tlp-5.0": "IETF-Trust-TLP-5.0",
    "ogl-uk-3.0": "OGL-UK-3.0",
}
_FIELD_ORDER: tuple[MetadataField, ...] = (
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
)
_SUPPORTED_FORMATS = frozenset(get_args(SourceFormat))
_SOURCE_PRECEDENCE = {
    source: rank for rank, source in enumerate(METADATA_SOURCE_PRECEDENCE)
}
MetadataIntegrityCode = Literal[
    "bibliographic_identity_mismatch",
    "content_checksum_mismatch",
    "content_length_mismatch",
    "invalid_checksum",
    "record_identity_mismatch",
    "source_format_mismatch",
]


class MetadataIntegrityError(ValueError):
    """A typed refusal for contradictory metadata identity evidence."""

    def __init__(
        self, code: MetadataIntegrityCode, provenance: str, detail: str
    ) -> None:
        self.code = code
        self.provenance = provenance
        super().__init__(f"{code} at {provenance}: {detail}")


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


def _digest(value: object, *, field: str, provenance: str) -> str | None:
    if value is None:
        return None
    if (
        not isinstance(value, str)
        or len(value) != 64
        or any(character not in "0123456789abcdef" for character in value)
    ):
        raise MetadataIntegrityError(
            "invalid_checksum", provenance, f"{field} is not lowercase SHA-256"
        )
    return value


def _verify_declared_record_identities(
    values: Mapping[str, object], *, provenance: str
) -> None:
    schema = values.get("schema_version")
    identity_contracts: tuple[tuple[str, frozenset[str]], ...] = (
        ("record_identity_sha256", frozenset({"record_identity_sha256"})),
        (
            "receipt_identity_sha256",
            frozenset(
                {
                    "receipt_identity_sha256",
                    "retrieved_at",
                    *(
                        ("transport",)
                        if schema == "bijux.canon.corpus_acquisition_receipt.v1"
                        else ()
                    ),
                }
            ),
        ),
        ("lock_identity_sha256", frozenset({"lock_identity_sha256"})),
    )
    for field, excluded in identity_contracts:
        declared = values.get(field)
        if declared is None:
            continue
        expected = _digest(declared, field=field, provenance=provenance)
        core = {key: value for key, value in values.items() if key not in excluded}
        actual = hashlib.sha256(_canonical_json(core)).hexdigest()
        if expected != actual:
            raise MetadataIntegrityError(
                "record_identity_mismatch",
                provenance,
                f"{field} does not identify the supplied record",
            )


def _text(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    collapsed = " ".join(normalized.split())
    if not collapsed:
        raise ValueError("metadata text must not be empty")
    return collapsed


def _doi(value: str) -> str:
    normalized = _text(value)
    for prefix in ("https://doi.org/", "http://doi.org/", "doi:"):
        if normalized.casefold().startswith(prefix):
            normalized = normalized[len(prefix) :]
            break
    normalized = normalized.strip().lower()
    if _DOI.fullmatch(normalized) is None:
        raise ValueError("DOI must use a valid 10.<registrant>/<suffix> form")
    return normalized


def _uri(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value.strip())
    if any(character.isspace() for character in normalized):
        raise ValueError("URI must not contain whitespace")
    parts = urlsplit(normalized)
    if not parts.scheme:
        raise ValueError("URI must be absolute")
    scheme = parts.scheme.lower()
    if scheme in {"http", "https"}:
        if not parts.hostname:
            raise ValueError("HTTP URI must contain a host")
        host = parts.hostname.encode("idna").decode("ascii").lower()
        port = parts.port
        if port is not None and not (
            (scheme == "http" and port == 80) or (scheme == "https" and port == 443)
        ):
            host = f"{host}:{port}"
        userinfo = ""
        if parts.username is not None:
            userinfo = parts.username
            if parts.password is not None:
                userinfo = f"{userinfo}:{parts.password}"
            userinfo = f"{userinfo}@"
        parts = SplitResult(
            scheme, f"{userinfo}{host}", parts.path or "/", parts.query, parts.fragment
        )
    else:
        parts = SplitResult(
            scheme, parts.netloc, parts.path, parts.query, parts.fragment
        )
    return urlunsplit(parts)


def _authors(value: MetadataValue) -> tuple[str, ...]:
    values = value if isinstance(value, tuple) else (value,)
    result: list[str] = []
    identities: set[str] = set()
    for author in values:
        normalized = _text(author)
        identity = normalized.casefold()
        if identity not in identities:
            result.append(normalized)
            identities.add(identity)
    if not result:
        raise ValueError("authors must not be empty")
    return tuple(result)


def _date(value: str) -> str:
    normalized = _text(value)
    pdf_match = _PDF_DATE.match(normalized)
    if pdf_match is not None:
        year, month, day = pdf_match.groups()
        normalized = year
        if month is not None:
            normalized = f"{normalized}-{month}"
        if day is not None:
            normalized = f"{normalized}-{day}"
    if re.fullmatch(r"\d{4}", normalized):
        year = int(normalized)
        if year <= 0:
            raise ValueError("publication year must be positive")
        return normalized
    if re.fullmatch(r"\d{4}-\d{2}", normalized):
        date.fromisoformat(f"{normalized}-01")
        return normalized
    candidate = normalized.replace("Z", "+00:00")
    try:
        return datetime.fromisoformat(candidate).date().isoformat()
    except ValueError:
        return date.fromisoformat(normalized).isoformat()


def _language(value: str) -> str:
    parts = _text(value).replace("_", "-").split("-")
    if not all(part.isalnum() for part in parts):
        raise ValueError("language must use alphanumeric BCP 47 subtags")
    normalized = [parts[0].lower()]
    for part in parts[1:]:
        if len(part) == 2 and part.isalpha():
            normalized.append(part.upper())
        elif len(part) == 4 and part.isalpha():
            normalized.append(part.title())
        else:
            normalized.append(part.lower())
    return "-".join(normalized)


def _license(value: str) -> str:
    normalized = _text(value)
    return _SPDX_NAMES.get(normalized.casefold(), normalized)


def _relative_path(value: str) -> str:
    normalized = unicodedata.normalize("NFC", value)
    if not normalized or normalized.startswith("/") or "\\" in normalized:
        raise ValueError("relative path must be portable and non-empty")
    original_parts = normalized.split("/")
    if any(part in {"", ".."} for part in original_parts):
        raise ValueError("relative path must not contain empty or parent segments")
    path = PurePosixPath(normalized)
    canonical = path.as_posix()
    if canonical in {"", "."}:
        raise ValueError("relative path must identify a file")
    return canonical


def _normalize(field: MetadataField, value: MetadataValue) -> MetadataValue:
    if field == "authors":
        return _authors(value)
    if isinstance(value, tuple):
        raise ValueError(f"{field} requires one scalar value")
    if field == "doi":
        return _doi(value)
    if field in {"canonical_uri", "license_url"}:
        return _uri(value)
    if field == "publication_date":
        return _date(value)
    if field in {"title", "journal"}:
        return _text(value)
    if field == "language":
        return _language(value)
    if field == "license_expression":
        return _license(value)
    if field == "relative_path":
        return _relative_path(value)
    if field == "media_type":
        return normalize_media_type(value)
    raise ValueError("unsupported metadata field")


def _date_compatible(first: MetadataValue, second: MetadataValue) -> bool:
    return (
        isinstance(first, str)
        and isinstance(second, str)
        and (first.startswith(f"{second}-") or second.startswith(f"{first}-"))
    )


@dataclass(frozen=True, slots=True)
class SourceMetadataRecord:
    """Raw metadata supplied by one named source or extraction boundary."""

    provenance: str
    doi: str | None = None
    canonical_uri: str | None = None
    authors: tuple[str, ...] = ()
    publication_date: str | None = None
    title: str | None = None
    journal: str | None = None
    language: str | None = None
    license_expression: str | None = None
    license_url: str | None = None
    relative_path: str | None = None
    media_type: str | None = None
    source: MetadataSource = "embedded_parser"
    source_format: SourceFormat | None = None
    source_content_sha256: str | None = None
    source_byte_length: int | None = None
    provenance_sha256: str | None = None

    def __post_init__(self) -> None:
        if not self.provenance:
            raise ValueError("SourceMetadataRecord.provenance must not be empty")
        if self.source not in _SOURCE_PRECEDENCE:
            raise ValueError("SourceMetadataRecord.source is unsupported")
        if (
            self.source_format is not None
            and self.source_format not in _SUPPORTED_FORMATS
        ):
            raise ValueError("SourceMetadataRecord.source_format is unsupported")
        _digest(
            self.source_content_sha256,
            field="source_content_sha256",
            provenance=self.provenance,
        )
        if self.source_byte_length is not None and (
            not isinstance(self.source_byte_length, int)
            or isinstance(self.source_byte_length, bool)
            or self.source_byte_length < 0
        ):
            raise ValueError(
                "SourceMetadataRecord.source_byte_length must be non-negative"
            )
        if self.provenance_sha256 is not None and (
            not self.provenance_sha256.startswith("sha256:")
            or len(self.provenance_sha256) != 71
            or any(
                character not in "0123456789abcdef"
                for character in self.provenance_sha256[7:]
            )
        ):
            raise ValueError("SourceMetadataRecord.provenance_sha256 must be SHA-256")

    @classmethod
    def from_mapping(
        cls,
        values: Mapping[str, object],
        *,
        provenance: str,
        source: MetadataSource = "embedded_parser",
    ) -> SourceMetadataRecord:
        """Read and identity-check one immutable metadata input record."""

        _verify_declared_record_identities(values, provenance=provenance)

        license_value = values.get("license")
        license_mapping = license_value if isinstance(license_value, Mapping) else {}
        authors_value = values.get("authors", ())
        if not isinstance(authors_value, Sequence) or isinstance(authors_value, str):
            raise ValueError("metadata authors must be a sequence of strings")
        if any(not isinstance(author, str) for author in authors_value):
            raise ValueError("metadata authors must contain only strings")

        def optional_string(value: object, field: str) -> str | None:
            if value is None:
                return None
            if not isinstance(value, str):
                raise ValueError(f"metadata {field} must be a string")
            return value

        publication_value = values.get("publication_date")
        if publication_value is None and "publication_year" in values:
            year = values["publication_year"]
            if not isinstance(year, int) or isinstance(year, bool):
                raise ValueError("metadata publication_year must be an integer")
            publication_value = str(year)

        content_digests = {
            digest
            for digest in (
                _digest(values.get("sha256"), field="sha256", provenance=provenance),
                _digest(
                    values.get("source_content_sha256"),
                    field="source_content_sha256",
                    provenance=provenance,
                ),
            )
            if digest is not None
        }
        if len(content_digests) > 1:
            raise MetadataIntegrityError(
                "content_checksum_mismatch",
                provenance,
                "sha256 and source_content_sha256 disagree",
            )
        byte_length_value = values.get("byte_count", values.get("byte_length"))
        if byte_length_value is not None and (
            not isinstance(byte_length_value, int)
            or isinstance(byte_length_value, bool)
            or byte_length_value < 0
        ):
            raise ValueError("metadata byte count must be a non-negative integer")
        format_value = values.get("format_id")
        if format_value is not None and (
            not isinstance(format_value, str) or format_value not in _SUPPORTED_FORMATS
        ):
            raise ValueError("metadata format_id is unsupported")

        return cls(
            provenance=provenance,
            doi=optional_string(values.get("doi"), "doi"),
            canonical_uri=optional_string(values.get("canonical_uri"), "canonical_uri"),
            authors=tuple(authors_value),
            publication_date=optional_string(publication_value, "publication_date"),
            title=optional_string(values.get("title"), "title"),
            journal=optional_string(values.get("journal"), "journal"),
            language=optional_string(values.get("language"), "language"),
            license_expression=optional_string(
                license_mapping.get("expression"), "license.expression"
            ),
            license_url=optional_string(license_mapping.get("url"), "license.url"),
            relative_path=optional_string(
                values.get("local_path", values.get("relative_path")),
                "relative_path",
            ),
            media_type=optional_string(values.get("media_type"), "media_type"),
            source=source,
            source_format=cast(SourceFormat | None, format_value),
            source_content_sha256=next(iter(content_digests), None),
            source_byte_length=byte_length_value,
            provenance_sha256=_identity(dict(values)),
        )

    @property
    def identity(self) -> str:
        """Return the exact mapping hash or a deterministic constructed-record hash."""

        if self.provenance_sha256 is not None:
            return self.provenance_sha256
        return _identity(
            {
                "fields": {
                    field: getattr(self, field)
                    for field in _FIELD_ORDER
                    if getattr(self, field) is not None and getattr(self, field) != ()
                },
                "provenance": self.provenance,
                "source": self.source,
                "source_format": self.source_format,
                "source_byte_length": self.source_byte_length,
                "source_content_sha256": self.source_content_sha256,
            }
        )

    def raw_values(self) -> tuple[tuple[MetadataField, MetadataValue], ...]:
        values: list[tuple[MetadataField, MetadataValue]] = []
        for field in _FIELD_ORDER:
            value = getattr(self, field)
            if value is not None and value != ():
                values.append((field, value))
        return tuple(values)

    def evidence(self) -> MetadataProvenanceRecord:
        """Return immutable evidence for this complete contributing record."""

        return MetadataProvenanceRecord(
            source=self.source,
            provenance=self.provenance,
            provenance_sha256=self.identity,
            format_id=self.source_format,
            source_content_sha256=self.source_content_sha256,
            source_byte_length=self.source_byte_length,
            fields=tuple(sorted(field for field, _ in self.raw_values())),
        )


def normalize_source_metadata(
    source: DiscoveredSource,
    *,
    format_id: SourceFormat,
    records: Iterable[SourceMetadataRecord] = (),
) -> CanonicalSourceMetadata:
    """Resolve typed precedence while retaining inputs, normalization, and conflict."""

    supplied_records = tuple(records)
    supplied: tuple[SourceMetadataRecord, ...] = (
        SourceMetadataRecord(
            provenance="source-discovery",
            relative_path=source.relative_path,
            media_type=source.media_type,
            source="source_discovery",
            source_format=format_id,
            source_content_sha256=source.content_sha256,
            source_byte_length=source.byte_length,
        ),
    ) + supplied_records
    if not any(record.title is not None for record in supplied_records):
        supplied += (
            SourceMetadataRecord(
                provenance=f"filename:{source.relative_path}",
                title=PurePosixPath(source.relative_path).stem,
                source="filename_fallback",
                source_format=format_id,
                source_content_sha256=source.content_sha256,
                source_byte_length=source.byte_length,
            ),
        )
    supplied = tuple(
        sorted(
            supplied,
            key=lambda record: (
                _SOURCE_PRECEDENCE[record.source],
                record.provenance,
                record.identity,
            ),
        )
    )
    candidates: dict[MetadataField, list[tuple[RawMetadataValue, MetadataValue]]] = {
        field: [] for field in _FIELD_ORDER
    }
    for record in supplied:
        if record.source_format is not None and record.source_format != format_id:
            raise MetadataIntegrityError(
                "source_format_mismatch",
                record.provenance,
                "metadata record declares a different admitted format",
            )
        if (
            record.source_content_sha256 is not None
            and record.source_content_sha256 != source.content_sha256
        ):
            raise MetadataIntegrityError(
                "content_checksum_mismatch",
                record.provenance,
                "metadata record identifies different source bytes",
            )
        if (
            record.source_byte_length is not None
            and record.source_byte_length != source.byte_length
        ):
            raise MetadataIntegrityError(
                "content_length_mismatch",
                record.provenance,
                "metadata record identifies a different source length",
            )
        record_normalized: dict[MetadataField, MetadataValue] = {}
        for field, value in record.raw_values():
            normalized = _normalize(field, value)
            record_normalized[field] = normalized
            raw = RawMetadataValue(
                field=field,
                value=value,
                normalized_value=normalized,
                source=record.source,
                provenance=record.provenance,
                provenance_sha256=record.identity,
            )
            candidates[field].append((raw, normalized))
        record_doi = record_normalized.get("doi")
        record_uri = record_normalized.get("canonical_uri")
        if isinstance(record_doi, str) and isinstance(record_uri, str):
            try:
                uri_doi = _doi(record_uri)
            except ValueError:
                pass
            else:
                if uri_doi != record_doi:
                    raise MetadataIntegrityError(
                        "bibliographic_identity_mismatch",
                        record.provenance,
                        "DOI and DOI canonical URI disagree",
                    )

    selected: dict[MetadataField, MetadataValue] = {}
    selected_inputs: list[RawMetadataValue] = []
    conflicts: list[MetadataConflict] = []
    for field in _FIELD_ORDER:
        field_candidates = candidates[field]
        if not field_candidates:
            continue
        selected_raw, selected_value = field_candidates[0]
        selected[field] = selected_value
        selected_inputs.append(selected_raw)
        alternatives = tuple(
            raw
            for raw, normalized in field_candidates[1:]
            if normalized != selected_value
            and not (
                field == "publication_date"
                and _date_compatible(selected_value, normalized)
            )
        )
        if alternatives:
            conflicts.append(MetadataConflict(field, selected_raw, alternatives))

    raw_values = tuple(
        sorted(
            (
                raw
                for field_candidates in candidates.values()
                for raw, _ in field_candidates
            ),
            key=lambda item: (
                item.field,
                _SOURCE_PRECEDENCE[item.source],
                item.provenance,
                item.provenance_sha256,
            ),
        )
    )
    authors = selected.get("authors", ())
    if not isinstance(authors, tuple):
        raise AssertionError("authors normalization must return a tuple")

    def scalar(field: MetadataField) -> str | None:
        value = selected.get(field)
        if value is None:
            return None
        if isinstance(value, tuple):
            raise AssertionError(f"{field} normalization must return a string")
        return value

    canonical_doi = scalar("doi")
    canonical_uri = scalar("canonical_uri")
    if canonical_doi is None and canonical_uri is not None:
        with suppress(ValueError):
            canonical_doi = _doi(canonical_uri)
    if canonical_doi is not None and canonical_uri is not None:
        try:
            uri_doi = _doi(canonical_uri)
        except ValueError:
            pass
        else:
            if uri_doi != canonical_doi:
                raise MetadataIntegrityError(
                    "bibliographic_identity_mismatch",
                    "resolved-metadata",
                    "selected DOI and DOI canonical URI disagree",
                )

    return CanonicalSourceMetadata(
        source_content_sha256=source.content_sha256,
        format_id=format_id,
        doi=canonical_doi,
        canonical_uri=canonical_uri,
        authors=authors,
        publication_date=scalar("publication_date"),
        title=scalar("title"),
        journal=scalar("journal"),
        language=scalar("language"),
        license_expression=scalar("license_expression"),
        license_url=scalar("license_url"),
        relative_path=scalar("relative_path") or source.relative_path,
        media_type=scalar("media_type") or source.media_type,
        provenance_records=tuple(record.evidence() for record in supplied),
        selected_values=tuple(sorted(selected_inputs, key=lambda item: item.field)),
        raw_values=raw_values,
        conflicts=tuple(sorted(conflicts, key=lambda conflict: conflict.field)),
    )


__all__ = [
    "MetadataIntegrityCode",
    "MetadataIntegrityError",
    "SourceMetadataRecord",
    "normalize_source_metadata",
]
