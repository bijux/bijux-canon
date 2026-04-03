# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from typing import Any

from bijux_vex.core.errors import ValidationError

CURRENT_VECTOR_METADATA_VERSION = 2


def migrate_vector_metadata(payload: dict[str, Any]) -> dict[str, Any]:
    version_raw = payload.get("schema_version", 0)
    try:
        version = int(version_raw)
    except Exception as exc:
        raise ValidationError(message="Invalid metadata schema_version") from exc
    if version > CURRENT_VECTOR_METADATA_VERSION:
        raise ValidationError(
            message=(
                f"Unsupported metadata schema_version {version}; "
                f"max supported is {CURRENT_VECTOR_METADATA_VERSION}"
            )
        )
    if version == CURRENT_VECTOR_METADATA_VERSION:
        return dict(payload)
    migrated = dict(payload)
    if version < 1:
        migrated["doc_id"] = migrated.get("doc_id") or migrated.get("document_id", "")
        migrated["chunk_id"] = migrated.get("chunk_id") or ""
        migrated["source_uri"] = migrated.get("source_uri")
        migrated["created_at"] = migrated.get("created_at")
        migrated["embedding"] = migrated.get("embedding") or {}
        migrated["embedding_ref"] = migrated.get("embedding_ref") or {}
        tags = migrated.get("tags") or []
        if not isinstance(tags, (list, tuple)):
            tags = [str(tags)]
        migrated["tags"] = list(tags)
        migrated["schema_version"] = 1
        version = 1
    if version < 2:
        migrated["embedding_ref"] = migrated.get("embedding_ref") or {}
        migrated["schema_version"] = CURRENT_VECTOR_METADATA_VERSION
    return migrated


__all__ = ["CURRENT_VECTOR_METADATA_VERSION", "migrate_vector_metadata"]
