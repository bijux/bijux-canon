# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_vex.core.errors import ValidationError
from bijux_vex.infra.adapters.metadata_migrations import (
    CURRENT_VECTOR_METADATA_VERSION,
    migrate_vector_metadata,
)


def test_migrate_vector_metadata_adds_schema_version() -> None:
    payload = {"doc_id": "doc-1", "tags": ("a", "b")}
    migrated = migrate_vector_metadata(payload)
    assert migrated["schema_version"] == CURRENT_VECTOR_METADATA_VERSION
    assert migrated["doc_id"] == "doc-1"
    assert migrated["tags"] == ["a", "b"]


def test_migrate_vector_metadata_rejects_future_version() -> None:
    payload = {"schema_version": CURRENT_VECTOR_METADATA_VERSION + 1}
    with pytest.raises(ValidationError):
        migrate_vector_metadata(payload)
