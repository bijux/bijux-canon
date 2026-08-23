# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Verified corpus-lock loading for canonical directory ingestion."""

from __future__ import annotations

import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass, replace
from pathlib import Path, PurePosixPath
from typing import Literal, cast

from bijux_canon_ingest.application.source_metadata import (
    MetadataIntegrityError,
    SourceMetadataRecord,
)
from bijux_canon_ingest.domain.source_admission import normalize_media_type
from bijux_canon_ingest.domain.source_discovery import DiscoveredSource

CorpusLockIssueCode = Literal[
    "acquisition_receipt_invalid",
    "ambiguous_lock",
    "content_checksum_mismatch",
    "content_length_mismatch",
    "duplicate_source",
    "extra_source",
    "license_missing",
    "locked_path_invalid",
    "lock_identity_mismatch",
    "malformed_lock",
    "manifest_invalid",
    "media_type_mismatch",
    "missing_source",
    "source_count_mismatch",
    "source_record_invalid",
    "unsupported_lock_schema",
]

_LOCK_SCHEMAS = frozenset(
    {
        "bijux.canon.parser_source_lock.v1",
        "bijux.canon.research_corpus_lock.v1",
    }
)
_MAX_RECORD_BYTES = 16 * 1024 * 1024


class CorpusLockError(ValueError):
    """A typed refusal for invalid or contradictory corpus-lock evidence."""

    def __init__(self, code: CorpusLockIssueCode, provenance: str, detail: str) -> None:
        self.code = code
        self.provenance = provenance
        super().__init__(f"{code} at {provenance}: {detail}")


@dataclass(frozen=True, slots=True)
class VerifiedLockedSource:
    """Verified metadata records for one discovered immutable source."""

    filesystem_path: Path
    records: tuple[SourceMetadataRecord, ...]


@dataclass(frozen=True, slots=True)
class VerifiedCorpusLock:
    """One verified lock and its exact discovered-source coverage."""

    schema_version: str
    lock_identity_sha256: str
    discovery: Literal["automatic", "explicit"]
    sources: tuple[VerifiedLockedSource, ...]

    def manifest(self) -> dict[str, object]:
        """Return portable lock evidence without leaking host filesystem paths."""

        return {
            "discovery": self.discovery,
            "lock_identity_sha256": self.lock_identity_sha256,
            "schema_version": self.schema_version,
            "source_count": len(self.sources),
            "status": "verified",
        }

    def records_for(self, source: DiscoveredSource) -> tuple[SourceMetadataRecord, ...]:
        """Return verified records for one source from this exact discovery pass."""

        source_path = source.filesystem_path.resolve()
        for locked in self.sources:
            if locked.filesystem_path == source_path:
                return locked.records
        raise CorpusLockError(
            "missing_source",
            source.relative_path,
            "verified corpus lock has no record for discovered source",
        )


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _pairs(pairs: list[tuple[str, object]]) -> dict[str, object]:
    result: dict[str, object] = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"duplicate JSON key: {key}")
        result[key] = value
    return result


def _read_bytes(
    path: Path,
    *,
    provenance: str,
    code: CorpusLockIssueCode = "manifest_invalid",
) -> bytes:
    if path.is_symlink() or not path.is_file():
        raise CorpusLockError(code, provenance, "record is not a regular file")
    size = path.stat().st_size
    if size > _MAX_RECORD_BYTES:
        raise CorpusLockError(
            code, provenance, "record exceeds the metadata size bound"
        )
    return path.read_bytes()


def _read_object(path: Path, *, code: CorpusLockIssueCode) -> dict[str, object]:
    provenance = path.as_posix()
    body = _read_bytes(path, provenance=provenance, code=code)
    try:
        value = json.loads(body.decode("utf-8"), object_pairs_hook=_pairs)
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CorpusLockError(
            code, provenance, "record is not canonical JSON"
        ) from error
    if not isinstance(value, dict):
        raise CorpusLockError(code, provenance, "record must be a JSON object")
    return cast(dict[str, object], value)


def _read_object_lines(
    body: bytes, *, provenance: str
) -> tuple[dict[str, object], ...]:
    try:
        lines = body.decode("utf-8").splitlines()
        values = [json.loads(line, object_pairs_hook=_pairs) for line in lines]
    except (UnicodeDecodeError, json.JSONDecodeError, ValueError) as error:
        raise CorpusLockError(
            "source_record_invalid", provenance, "portfolio is not canonical JSONL"
        ) from error
    if not lines or any(
        not line or not isinstance(value, dict)
        for line, value in zip(lines, values, strict=True)
    ):
        raise CorpusLockError(
            "source_record_invalid",
            provenance,
            "portfolio must contain one JSON object per non-empty line",
        )
    return tuple(cast(dict[str, object], value) for value in values)


def _required_text(values: Mapping[str, object], field: str, *, provenance: str) -> str:
    value = values.get(field)
    if not isinstance(value, str) or not value:
        raise CorpusLockError(
            "malformed_lock", provenance, f"{field} must be a non-empty string"
        )
    return value


def _required_sha256(
    values: Mapping[str, object], field: str, *, provenance: str
) -> str:
    value = _required_text(values, field, provenance=provenance)
    if len(value) != 64 or any(
        character not in "0123456789abcdef" for character in value
    ):
        raise CorpusLockError(
            "malformed_lock", provenance, f"{field} must be lowercase SHA-256"
        )
    return value


def _safe_path(base: Path, value: object, *, provenance: str) -> Path:
    if (
        not isinstance(value, str)
        or not value
        or value.startswith("/")
        or "\\" in value
    ):
        raise CorpusLockError(
            "locked_path_invalid",
            provenance,
            "locked path must be portable and relative",
        )
    relative = PurePosixPath(value)
    if any(part in {"", ".", ".."} for part in relative.parts):
        raise CorpusLockError(
            "locked_path_invalid", provenance, "locked path contains unsafe segments"
        )
    root = base.resolve()
    resolved = root.joinpath(*relative.parts).resolve()
    if not resolved.is_relative_to(root):
        raise CorpusLockError(
            "locked_path_invalid", provenance, "locked path escapes its record root"
        )
    return resolved


def _validate_license(values: Mapping[str, object], *, provenance: str) -> None:
    license_value = values.get("license")
    if not isinstance(license_value, Mapping) or any(
        not isinstance(license_value.get(field), str) or not license_value.get(field)
        for field in ("expression", "url")
    ):
        raise CorpusLockError(
            "license_missing",
            provenance,
            "locked source requires license expression and URL",
        )


def _validate_lock_identity(lock: Mapping[str, object], *, provenance: str) -> str:
    expected = _required_sha256(lock, "lock_identity_sha256", provenance=provenance)
    core = {key: value for key, value in lock.items() if key != "lock_identity_sha256"}
    if _sha256(_canonical_json(core)) != expected:
        raise CorpusLockError(
            "lock_identity_mismatch",
            provenance,
            "declared lock identity does not match canonical lock content",
        )
    return expected


def _lock_sources(
    lock: Mapping[str, object], *, provenance: str, require_total: bool = True
) -> tuple[Mapping[str, object], ...]:
    sources = lock.get("sources")
    count = lock.get("source_count")
    if (
        not isinstance(sources, Sequence)
        or isinstance(sources, (str, bytes))
        or not isinstance(count, int)
        or isinstance(count, bool)
        or count != len(sources)
    ):
        raise CorpusLockError(
            "source_count_mismatch",
            provenance,
            "source_count must equal the lock source array length",
        )
    if any(not isinstance(source, Mapping) for source in sources):
        raise CorpusLockError(
            "malformed_lock", provenance, "every locked source must be an object"
        )
    typed_sources = tuple(cast(Mapping[str, object], source) for source in sources)
    byte_counts = [source.get("byte_count") for source in typed_sources]
    total_bytes = lock.get("total_bytes")
    if (
        any(
            not isinstance(value, int) or isinstance(value, bool) or value < 0
            for value in byte_counts
        )
        or (require_total and not isinstance(total_bytes, int))
        or isinstance(total_bytes, bool)
        or (
            total_bytes is not None
            and total_bytes != sum(cast(int, value) for value in byte_counts)
        )
    ):
        raise CorpusLockError(
            "content_length_mismatch",
            provenance,
            "total_bytes must equal the sum of locked source lengths",
        )
    return typed_sources


def _match_discovered_source(
    locked: Mapping[str, object],
    *,
    base: Path,
    discovered: Mapping[Path, DiscoveredSource],
    provenance: str,
) -> tuple[Path, DiscoveredSource]:
    path = _safe_path(base, locked.get("local_path"), provenance=provenance)
    source = discovered.get(path)
    if source is None:
        raise CorpusLockError(
            "missing_source",
            provenance,
            "locked source is absent from the discovered directory",
        )
    expected_sha256 = _required_sha256(locked, "sha256", provenance=provenance)
    if source.content_sha256 != expected_sha256:
        raise CorpusLockError(
            "content_checksum_mismatch",
            provenance,
            "discovered source bytes do not match the lock",
        )
    byte_count = locked.get("byte_count")
    if (
        not isinstance(byte_count, int)
        or isinstance(byte_count, bool)
        or source.byte_length != byte_count
    ):
        raise CorpusLockError(
            "content_length_mismatch",
            provenance,
            "discovered source length does not match the lock",
        )
    media_type = locked.get("media_type")
    format_id = locked.get("format_id")
    normalized_locked_media = (
        normalize_media_type(media_type) if isinstance(media_type, str) else None
    )
    normalized_discovered_media = normalize_media_type(source.media_type)
    compatible_media = (
        normalized_locked_media == normalized_discovered_media
        or (
            format_id in {None, "jats"}
            and {normalized_locked_media, normalized_discovered_media}
            == {"application/xml", "application/jats+xml"}
        )
        or (
            format_id == "markdown"
            and {normalized_locked_media, normalized_discovered_media}
            == {"text/plain", "text/markdown"}
        )
    )
    if not compatible_media:
        raise CorpusLockError(
            "media_type_mismatch",
            provenance,
            "discovered media type does not match the lock",
        )
    _validate_license(locked, provenance=provenance)
    return path, source


def _require_matching_fields(
    expected: Mapping[str, object],
    observed: Mapping[str, object],
    fields: tuple[str, ...],
    *,
    code: CorpusLockIssueCode,
    provenance: str,
) -> None:
    drift = [field for field in fields if expected.get(field) != observed.get(field)]
    if drift:
        raise CorpusLockError(
            code,
            provenance,
            f"linked records disagree on fields: {', '.join(drift)}",
        )


def _metadata_record(
    values: Mapping[str, object],
    *,
    provenance: str,
    source: Literal["corpus_lock", "acquisition_receipt"],
    code: CorpusLockIssueCode,
) -> SourceMetadataRecord:
    try:
        return SourceMetadataRecord.from_mapping(
            values, provenance=provenance, source=source
        )
    except (MetadataIntegrityError, ValueError) as error:
        raise CorpusLockError(code, provenance, str(error)) from error


def _verify_parser_sources(
    lock: Mapping[str, object],
    *,
    lock_path: Path,
    lock_identity: str,
    sources: tuple[Mapping[str, object], ...],
    discovered: Mapping[Path, DiscoveredSource],
) -> tuple[VerifiedLockedSource, ...]:
    provenance = lock_path.as_posix()
    portfolio_path = _safe_path(
        lock_path.parent, lock.get("portfolio_uri"), provenance=provenance
    )
    portfolio = _read_bytes(portfolio_path, provenance=portfolio_path.as_posix())
    if _sha256(portfolio) != _required_sha256(
        lock, "portfolio_sha256", provenance=provenance
    ):
        raise CorpusLockError(
            "manifest_invalid", provenance, "source portfolio checksum mismatch"
        )
    portfolio_records = _read_object_lines(
        portfolio, provenance=portfolio_path.as_posix()
    )
    portfolio_by_id: dict[str, Mapping[str, object]] = {}
    for record in portfolio_records:
        source_id = _required_text(record, "parser_source_id", provenance=provenance)
        if source_id in portfolio_by_id:
            raise CorpusLockError(
                "duplicate_source",
                provenance,
                "source portfolio identity is duplicated",
            )
        portfolio_by_id[source_id] = record
    if len(portfolio_by_id) != len(sources):
        raise CorpusLockError(
            "source_count_mismatch",
            provenance,
            "source portfolio and corpus lock have different source counts",
        )

    verified: list[VerifiedLockedSource] = []
    identities: set[str] = set()
    for locked in sources:
        source_id = _required_text(locked, "parser_source_id", provenance=provenance)
        source_provenance = f"corpus-lock:{lock_identity}:{source_id}"
        if source_id in identities:
            raise CorpusLockError(
                "duplicate_source", source_provenance, "source identity is duplicated"
            )
        identities.add(source_id)
        path, _ = _match_discovered_source(
            locked,
            base=lock_path.parent,
            discovered=discovered,
            provenance=source_provenance,
        )
        source_record_path = _safe_path(
            lock_path.parent,
            locked.get("source_record_uri"),
            provenance=source_provenance,
        )
        receipt_path = _safe_path(
            lock_path.parent,
            locked.get("acquisition_receipt_uri"),
            provenance=source_provenance,
        )
        source_record = _read_object(source_record_path, code="source_record_invalid")
        receipt = _read_object(receipt_path, code="acquisition_receipt_invalid")
        source_identity = _required_sha256(
            locked, "source_record_identity_sha256", provenance=source_provenance
        )
        receipt_identity = _required_sha256(
            locked,
            "acquisition_receipt_identity_sha256",
            provenance=source_provenance,
        )
        if source_record.get("record_identity_sha256") != source_identity:
            raise CorpusLockError(
                "source_record_invalid",
                source_provenance,
                "lock and source-record identities disagree",
            )
        portfolio_record = portfolio_by_id.get(source_id)
        if (
            portfolio_record is None
            or {
                **portfolio_record,
                "record_identity_sha256": source_identity,
            }
            != source_record
        ):
            raise CorpusLockError(
                "source_record_invalid",
                source_provenance,
                "source portfolio and referenced source record disagree",
            )
        if receipt.get("receipt_identity_sha256") != receipt_identity:
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "lock and acquisition-receipt identities disagree",
            )
        if (
            source_record.get("schema_version") != "bijux.canon.parser_source.v1"
            or receipt.get("schema_version")
            != "bijux.canon.parser_source_acquisition.v1"
            or receipt.get("state") != "acquired"
        ):
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "source and acquisition records use unsupported states or schemas",
            )
        _validate_license(source_record, provenance=source_record_path.as_posix())
        _validate_license(receipt, provenance=receipt_path.as_posix())
        _require_matching_fields(
            locked,
            receipt,
            (
                "parser_source_id",
                "source_record_identity_sha256",
                "format_id",
                "local_path",
                "media_type",
                "byte_count",
                "sha256",
                "license",
            ),
            code="acquisition_receipt_invalid",
            provenance=source_provenance,
        )
        transport = receipt.get("transport")
        license_evidence = receipt.get("license_evidence")
        if not isinstance(transport, Mapping) or (
            locked.get("transport_response_sha256") != transport.get("response_sha256")
            or locked.get("transport_response_byte_count")
            != transport.get("response_byte_count")
            or locked.get("retrieved_at") != receipt.get("retrieved_at")
        ):
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "lock and acquisition transport evidence disagree",
            )
        if not isinstance(license_evidence, Mapping) or (
            locked.get("license_evidence_sha256") != license_evidence.get("sha256")
        ):
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "lock and license evidence checksums disagree",
            )
        _require_matching_fields(
            locked,
            source_record,
            ("parser_source_id", "format_id", "canonical_uri", "license"),
            code="source_record_invalid",
            provenance=source_provenance,
        )
        lock_record = _metadata_record(
            locked,
            provenance=source_provenance,
            source="corpus_lock",
            code="malformed_lock",
        )
        reviewed_record = _metadata_record(
            source_record,
            provenance=f"{source_provenance}:source-record",
            source="corpus_lock",
            code="source_record_invalid",
        )
        receipt_record = _metadata_record(
            receipt,
            provenance=f"acquisition-receipt:{receipt_identity}:{source_id}",
            source="acquisition_receipt",
            code="acquisition_receipt_invalid",
        )
        verified.append(
            VerifiedLockedSource(path, (lock_record, reviewed_record, receipt_record))
        )
    if set(portfolio_by_id) != identities:
        raise CorpusLockError(
            "extra_source",
            provenance,
            "source portfolio and corpus lock have different identities",
        )
    return tuple(sorted(verified, key=lambda item: item.filesystem_path.as_posix()))


def _research_manifest_path(lock_path: Path) -> Path:
    return lock_path.parent / "corpus" / "corpus-manifest.json"


def _verify_research_sources(
    lock: Mapping[str, object],
    *,
    lock_path: Path,
    lock_identity: str,
    sources: tuple[Mapping[str, object], ...],
    discovered: Mapping[Path, DiscoveredSource],
) -> tuple[VerifiedLockedSource, ...]:
    provenance = lock_path.as_posix()
    manifest_path = _research_manifest_path(lock_path)
    manifest_body = _read_bytes(manifest_path, provenance=manifest_path.as_posix())
    if _sha256(manifest_body) != _required_sha256(
        lock, "manifest_sha256", provenance=provenance
    ):
        raise CorpusLockError(
            "manifest_invalid", provenance, "materialization manifest checksum mismatch"
        )
    manifest = _read_object(manifest_path, code="manifest_invalid")
    if (
        manifest.get("schema_version") != "bijux.canon.full_text_jats_portfolio.v1"
        or manifest.get("state") != "materialized"
    ):
        raise CorpusLockError(
            "manifest_invalid", provenance, "materialization manifest state is invalid"
        )
    manifest_sources = _lock_sources(
        manifest, provenance=manifest_path.as_posix(), require_total=False
    )
    identity_rows: list[dict[str, object]] = []
    manifest_by_id: dict[str, Mapping[str, object]] = {}
    for item in manifest_sources:
        source_id = _required_text(item, "source_id", provenance=provenance)
        if source_id in manifest_by_id:
            raise CorpusLockError(
                "duplicate_source", provenance, "materialization source is duplicated"
            )
        manifest_by_id[source_id] = item
        identity_rows.append(
            {
                "acquisition_receipt_identity_sha256": _required_sha256(
                    item,
                    "acquisition_receipt_identity_sha256",
                    provenance=provenance,
                ),
                "sha256": _required_sha256(item, "sha256", provenance=provenance),
                "source_id": source_id,
                "source_record_identity_sha256": _required_sha256(
                    item, "source_record_identity_sha256", provenance=provenance
                ),
            }
        )
    portfolio_identity = _sha256(
        _canonical_json(
            sorted(identity_rows, key=lambda item: cast(str, item["source_id"]))
        )
    )
    if (
        manifest.get("portfolio_identity_sha256") != portfolio_identity
        or lock.get("manifest_identity_sha256") != portfolio_identity
    ):
        raise CorpusLockError(
            "manifest_invalid", provenance, "materialization identity is invalid"
        )

    verified: list[VerifiedLockedSource] = []
    locked_ids: set[str] = set()
    for locked in sources:
        source_id = _required_text(locked, "source_id", provenance=provenance)
        source_provenance = f"corpus-lock:{lock_identity}:{source_id}"
        if source_id in locked_ids:
            raise CorpusLockError(
                "duplicate_source", source_provenance, "source identity is duplicated"
            )
        locked_ids.add(source_id)
        path, _ = _match_discovered_source(
            locked,
            base=lock_path.parent,
            discovered=discovered,
            provenance=source_provenance,
        )
        materialized = manifest_by_id.get(source_id)
        if materialized is None:
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "materialization manifest lacks the locked source",
            )
        materialized_path = _safe_path(
            manifest_path.parent,
            materialized.get("local_path"),
            provenance=source_provenance,
        )
        if materialized_path != path:
            raise CorpusLockError(
                "acquisition_receipt_invalid",
                source_provenance,
                "lock and materialization paths identify different files",
            )
        _validate_license(materialized, provenance=source_provenance)
        _require_matching_fields(
            locked,
            materialized,
            (
                "source_id",
                "source_record_identity_sha256",
                "acquisition_receipt_identity_sha256",
                "doi",
                "title",
                "authors",
                "journal",
                "publication_year",
                "media_type",
                "byte_count",
                "sha256",
                "license",
            ),
            code="acquisition_receipt_invalid",
            provenance=source_provenance,
        )
        lock_record = replace(
            _metadata_record(
                locked,
                provenance=source_provenance,
                source="corpus_lock",
                code="malformed_lock",
            ),
            source_format="jats",
        )
        acquisition_record = replace(
            _metadata_record(
                materialized,
                provenance=(
                    "acquisition-manifest:"
                    f"{materialized['acquisition_receipt_identity_sha256']}:{source_id}"
                ),
                source="acquisition_receipt",
                code="acquisition_receipt_invalid",
            ),
            source_format="jats",
        )
        verified.append(VerifiedLockedSource(path, (lock_record, acquisition_record)))
    if set(manifest_by_id) != locked_ids:
        raise CorpusLockError(
            "extra_source",
            provenance,
            "materialization manifest and corpus lock have different source sets",
        )
    return tuple(sorted(verified, key=lambda item: item.filesystem_path.as_posix()))


def _automatic_lock_path(root_path: Path) -> Path | None:
    root = root_path.resolve()
    candidates = [root / "corpus.lock.json", root.parent / "corpus.lock.json"]
    if root.parent.name == "corpus":
        candidates.append(root.parent.parent / "corpus.lock.json")
    existing = tuple(
        dict.fromkeys(candidate for candidate in candidates if candidate.exists())
    )
    if len(existing) > 1:
        raise CorpusLockError(
            "ambiguous_lock",
            root.as_posix(),
            "multiple automatic corpus locks are visible; select one explicitly",
        )
    return existing[0] if existing else None


def load_verified_corpus_lock(
    root_path: Path,
    sources: Sequence[DiscoveredSource],
    *,
    lock_path: Path | None = None,
) -> VerifiedCorpusLock | None:
    """Load an explicit or adjacent lock and verify exact discovery coverage."""

    selected_path = (
        lock_path.resolve()
        if lock_path is not None
        else _automatic_lock_path(root_path)
    )
    if selected_path is None:
        return None
    discovery_kind: Literal["automatic", "explicit"] = (
        "explicit" if lock_path is not None else "automatic"
    )
    lock = _read_object(selected_path, code="malformed_lock")
    provenance = selected_path.as_posix()
    schema = _required_text(lock, "schema_version", provenance=provenance)
    if schema not in _LOCK_SCHEMAS:
        raise CorpusLockError(
            "unsupported_lock_schema", provenance, f"unsupported schema {schema!r}"
        )
    identity = _validate_lock_identity(lock, provenance=provenance)
    locked_sources = _lock_sources(lock, provenance=provenance)
    discovered = {source.filesystem_path.resolve(): source for source in sources}
    if len(discovered) != len(sources):
        raise CorpusLockError(
            "duplicate_source", provenance, "discovery contains duplicate file paths"
        )
    if len(locked_sources) != len(discovered):
        code: CorpusLockIssueCode = (
            "missing_source"
            if len(locked_sources) > len(discovered)
            else "extra_source"
        )
        raise CorpusLockError(
            code,
            provenance,
            "corpus lock and discovered directory have different source counts",
        )
    if schema == "bijux.canon.parser_source_lock.v1":
        verified = _verify_parser_sources(
            lock,
            lock_path=selected_path,
            lock_identity=identity,
            sources=locked_sources,
            discovered=discovered,
        )
    else:
        verified = _verify_research_sources(
            lock,
            lock_path=selected_path,
            lock_identity=identity,
            sources=locked_sources,
            discovered=discovered,
        )
    verified_paths = {source.filesystem_path for source in verified}
    if verified_paths != set(discovered):
        raise CorpusLockError(
            "extra_source",
            provenance,
            "discovered directory contains a source absent from the corpus lock",
        )
    return VerifiedCorpusLock(schema, identity, discovery_kind, verified)


__all__ = [
    "CorpusLockError",
    "CorpusLockIssueCode",
    "VerifiedCorpusLock",
    "VerifiedLockedSource",
    "load_verified_corpus_lock",
]
