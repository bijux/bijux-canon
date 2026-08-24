# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic archive of immutable original source bytes."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import PurePosixPath
import re
import struct

from bijux_canon_ingest.application.canonical_ingest import CanonicalRetainedSource
from bijux_canon_runtime.model.artifact import canonical_json_bytes

_MAGIC = b"BIJUX-CANON-SOURCE-ARCHIVE-V1\n"
_HEADER_LENGTH = struct.Struct(">Q")


class SourceArchiveError(ValueError):
    """A retained source archive is malformed or fails content verification."""


@dataclass(frozen=True, slots=True)
class SourceArchiveEntry:
    """One verified byte range within a retained source archive."""

    relative_path: str
    media_type: str
    content_sha256: str
    byte_length: int
    data_offset: int
    content: bytes


def build_source_archive(sources: tuple[CanonicalRetainedSource, ...]) -> bytes:
    """Encode verified sources as one deterministic indexed binary payload."""
    if not sources:
        raise SourceArchiveError("source archive requires at least one source")
    ordered = tuple(sorted(sources, key=lambda item: item.relative_path))
    if len({item.relative_path for item in ordered}) != len(ordered):
        raise SourceArchiveError("source archive paths must be unique")
    offset = 0
    entries: list[dict[str, object]] = []
    payloads: list[bytes] = []
    for source in ordered:
        _validate_relative_path(source.relative_path)
        if hashlib.sha256(source.content).hexdigest() != source.content_sha256:
            raise SourceArchiveError("source archive input digest is invalid")
        entries.append(
            {
                "byte_length": len(source.content),
                "content_sha256": source.content_sha256,
                "data_offset": offset,
                "media_type": source.media_type,
                "relative_path": source.relative_path,
            }
        )
        payloads.append(source.content)
        offset += len(source.content)
    header = canonical_json_bytes(
        {
            "data_byte_length": offset,
            "entries": entries,
            "schema_version": "bijux.canon.ingest.source_archive.v1",
        }
    )
    return _MAGIC + _HEADER_LENGTH.pack(len(header)) + header + b"".join(payloads)


def read_source_archive(payload: bytes) -> tuple[SourceArchiveEntry, ...]:
    """Parse and verify every indexed range without filesystem extraction."""
    prefix_length = len(_MAGIC) + _HEADER_LENGTH.size
    if len(payload) < prefix_length or not payload.startswith(_MAGIC):
        raise SourceArchiveError("source archive header is invalid")
    header_length = _HEADER_LENGTH.unpack(
        payload[len(_MAGIC) : prefix_length]
    )[0]
    header_end = prefix_length + header_length
    if header_end > len(payload):
        raise SourceArchiveError("source archive header length is invalid")
    try:
        header_bytes = payload[prefix_length:header_end]
        header = json.loads(header_bytes)
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise SourceArchiveError("source archive index is unreadable") from error
    if (
        not isinstance(header, dict)
        or header.get("schema_version")
        != "bijux.canon.ingest.source_archive.v1"
        or not isinstance(header.get("entries"), list)
    ):
        raise SourceArchiveError("source archive index contract is invalid")
    if canonical_json_bytes(header) != header_bytes:
        raise SourceArchiveError("source archive index is not canonical")
    data = payload[header_end:]
    if header.get("data_byte_length") != len(data):
        raise SourceArchiveError("source archive data length is invalid")
    result: list[SourceArchiveEntry] = []
    expected_offset = 0
    paths: set[str] = set()
    for raw in header["entries"]:
        if not isinstance(raw, dict):
            raise SourceArchiveError("source archive entry is invalid")
        relative_path = raw.get("relative_path")
        media_type = raw.get("media_type")
        content_sha256 = raw.get("content_sha256")
        byte_length = raw.get("byte_length")
        data_offset = raw.get("data_offset")
        if (
            not isinstance(relative_path, str)
            or not isinstance(media_type, str)
            or not isinstance(content_sha256, str)
            or isinstance(byte_length, bool)
            or not isinstance(byte_length, int)
            or isinstance(data_offset, bool)
            or not isinstance(data_offset, int)
            or byte_length < 0
            or data_offset != expected_offset
            or "/" not in media_type
            or re.fullmatch(r"[0-9a-f]{64}", content_sha256) is None
        ):
            raise SourceArchiveError("source archive entry fields are invalid")
        _validate_relative_path(relative_path)
        if relative_path in paths:
            raise SourceArchiveError("source archive entry paths are duplicated")
        paths.add(relative_path)
        end = data_offset + byte_length
        if end > len(data):
            raise SourceArchiveError("source archive entry exceeds its data section")
        content = data[data_offset:end]
        if hashlib.sha256(content).hexdigest() != content_sha256:
            raise SourceArchiveError("source archive entry digest is invalid")
        result.append(
            SourceArchiveEntry(
                relative_path=relative_path,
                media_type=media_type,
                content_sha256=content_sha256,
                byte_length=byte_length,
                data_offset=data_offset,
                content=content,
            )
        )
        expected_offset = end
    if not result or expected_offset != len(data):
        raise SourceArchiveError("source archive data coverage is invalid")
    if [item.relative_path for item in result] != sorted(paths):
        raise SourceArchiveError("source archive entries are not canonically ordered")
    return tuple(result)


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if (
        not value
        or value.startswith("/")
        or "\\" in value
        or path.as_posix() != value
        or any(part in {"", ".", ".."} for part in path.parts)
    ):
        raise SourceArchiveError("source archive path is not portable")


__all__ = [
    "SourceArchiveEntry",
    "SourceArchiveError",
    "build_source_archive",
    "read_source_archive",
]
