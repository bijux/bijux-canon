# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stable cursor pagination for immutable Runtime responses."""

from __future__ import annotations

import base64
from collections.abc import Mapping, Sequence
from dataclasses import asdict, dataclass, is_dataclass
from enum import Enum
import hashlib
import json

from bijux_canon_runtime.model.artifact import canonical_json_bytes

MAX_PAGE_SIZE = 1000


@dataclass(frozen=True, slots=True)
class PageRequest:
    """One bounded page request using an opaque cursor or legacy offset."""

    limit: int = 100
    cursor: str | None = None
    offset: int | None = None

    def __post_init__(self) -> None:
        if not 1 <= self.limit <= MAX_PAGE_SIZE:
            raise ValueError(f"page limit must be between 1 and {MAX_PAGE_SIZE}")
        if self.offset is not None and self.offset < 0:
            raise ValueError("page offset must not be negative")
        if self.cursor is not None and self.offset not in {None, 0}:
            raise ValueError("page cursor and nonzero offset are mutually exclusive")


def paginate_collections(
    record: Mapping[str, object],
    *,
    collection_fields: Sequence[str],
    resource_identity: Mapping[str, object],
    request: PageRequest,
) -> dict[str, object]:
    """Slice immutable collections and bind the next cursor to their snapshot."""
    collections = {
        field: value
        for field in collection_fields
        if isinstance((value := record.get(field)), list | tuple)
    }
    result = {
        key: value if key in collections else _json_value(value)
        for key, value in record.items()
    }
    snapshot_sha256 = hashlib.sha256(
        canonical_json_bytes(
            {
                "collection_lengths": {
                    field: len(values) for field, values in collections.items()
                },
                "resource_identity": dict(resource_identity),
                "schema_version": "bijux.runtime.pagination-snapshot.v1",
            }
        )
    ).hexdigest()
    offset = _cursor_offset(request.cursor, snapshot_sha256)
    if request.cursor is None:
        offset = request.offset or 0
    for field, values in collections.items():
        result[field] = _json_value(values[offset : offset + request.limit])
    has_more = any(
        len(values) > offset + request.limit for values in collections.values()
    )
    next_offset = offset + request.limit if has_more else None
    result["page"] = {
        "limit": request.limit,
        "next_cursor": (
            _encode_cursor(snapshot_sha256, next_offset)
            if next_offset is not None
            else None
        ),
        "next_offset": next_offset,
        "offset": offset,
        "snapshot_sha256": snapshot_sha256,
    }
    return result


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if is_dataclass(value) and not isinstance(value, type):
        return _json_value(asdict(value))
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, tuple | list):
        return [_json_value(item) for item in value]
    return value


def _encode_cursor(snapshot_sha256: str, offset: int) -> str:
    payload = canonical_json_bytes(
        {
            "offset": offset,
            "schema_version": "bijux.runtime.cursor.v1",
            "snapshot_sha256": snapshot_sha256,
        }
    )
    checksum = hashlib.sha256(payload).digest()[:16]
    return base64.urlsafe_b64encode(payload + checksum).decode("ascii").rstrip("=")


def _cursor_offset(cursor: str | None, snapshot_sha256: str) -> int:
    if cursor is None:
        return 0
    try:
        padded = cursor + "=" * (-len(cursor) % 4)
        decoded = base64.b64decode(padded, altchars=b"-_", validate=True)
        if len(decoded) <= 16:
            raise ValueError
        payload, checksum = decoded[:-16], decoded[-16:]
        if hashlib.sha256(payload).digest()[:16] != checksum:
            raise ValueError
        record = json.loads(payload)
        if not isinstance(record, dict) or set(record) != {
            "offset",
            "schema_version",
            "snapshot_sha256",
        }:
            raise ValueError
        offset = record["offset"]
        if (
            record["schema_version"] != "bijux.runtime.cursor.v1"
            or record["snapshot_sha256"] != snapshot_sha256
            or isinstance(offset, bool)
            or not isinstance(offset, int)
            or offset < 0
        ):
            raise ValueError
    except (UnicodeEncodeError, ValueError, TypeError, json.JSONDecodeError) as exc:
        raise ValueError(
            "page cursor is invalid or belongs to another snapshot"
        ) from exc
    return offset


__all__ = ["MAX_PAGE_SIZE", "PageRequest", "paginate_collections"]
