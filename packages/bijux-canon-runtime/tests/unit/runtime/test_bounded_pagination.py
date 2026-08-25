from __future__ import annotations

import base64
import json
from pathlib import Path

import pytest

from bijux_canon_runtime.application.inspection_views import bounded_inspection_record
from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.runtime.inspection import (
    RuntimeInspectionError,
    RuntimeInspectionLimits,
    RuntimeRunInspector,
)
from bijux_canon_runtime.runtime.pagination import PageRequest, paginate_collections
from bijux_canon_runtime.runtime.persistence import (
    AtomicFilesystemArtifactPayloadStore,
)


def test_cursor_is_stable_and_rejected_for_another_snapshot() -> None:
    first = paginate_collections(
        {"items": [1, 2, 3]},
        collection_fields=("items",),
        resource_identity={"generation": "immutable-a"},
        request=PageRequest(limit=2),
    )
    first_page = first["page"]
    assert isinstance(first_page, dict)
    cursor = first_page["next_cursor"]
    assert isinstance(cursor, str)

    repeated = paginate_collections(
        {"items": [1, 2, 3]},
        collection_fields=("items",),
        resource_identity={"generation": "immutable-a"},
        request=PageRequest(limit=2),
    )
    assert repeated["page"] == first["page"]

    with pytest.raises(ValueError, match="another snapshot"):
        paginate_collections(
            {"items": [1, 2, 4]},
            collection_fields=("items",),
            resource_identity={"generation": "immutable-b"},
            request=PageRequest(limit=2, cursor=cursor),
        )


def test_page_request_enforces_limits_and_cursor_exclusivity() -> None:
    with pytest.raises(ValueError, match="between 1 and 1000"):
        PageRequest(limit=1001)
    with pytest.raises(ValueError, match="mutually exclusive"):
        PageRequest(limit=10, cursor="opaque", offset=1)


def test_run_inspection_stops_at_inventory_limit(tmp_path: Path) -> None:
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    for sequence in range(2):
        store.put(
            AddressedArtifact.from_json(
                {"sequence": sequence},
                schema_id="bijux.runtime.fixture.v1",
                producer="bijux-canon-runtime:test",
            )
        )
    inspector = RuntimeRunInspector(
        store,
        limits=RuntimeInspectionLimits(max_inventory_artifacts=1),
    )

    with pytest.raises(RuntimeInspectionError, match="inventory exceeds"):
        inspector.inspect("run-that-is-not-present")


def test_public_inspection_replaces_large_values_with_bounded_references() -> None:
    large_value = {"document": "x" * 1_060_000}
    record = bounded_inspection_record(
        {
            "artifacts": [
                {
                    "artifact_id": "sha256:" + "a" * 64,
                    "json_value": large_value,
                    "size_bytes": 1_060_000,
                }
            ],
            "claims": [
                {
                    "json_path": "$.claim",
                    "source_artifact_id": "sha256:" + "a" * 64,
                    "source_step_id": "reason",
                    "value": large_value,
                }
            ],
            "run_id": "run-large",
        }
    )
    page = paginate_collections(
        record,
        collection_fields=("artifacts", "claims"),
        resource_identity={"run_id": "run-large"},
        request=PageRequest(limit=20),
    )
    encoded = json.dumps(page, separators=(",", ":")).encode()

    assert len(encoded) < 10_000
    assert b"x" * 513 not in encoded
    assert page["collection_counts"] == {"artifacts": 1, "claims": 1}
    assert page["artifacts"][0]["json_value"]["byte_length"] > 1_000_000
    assert "inline" not in page["artifacts"][0]["json_value"]


def test_artifact_payload_access_is_deliberate_and_paginated(tmp_path: Path) -> None:
    store = AtomicFilesystemArtifactPayloadStore(tmp_path / "cas")
    artifact = AddressedArtifact.from_bytes(
        b"0123456789",
        schema_id="bijux.runtime.large-value.v1",
        media_type="application/octet-stream",
        producer="bijux-canon-runtime:test",
    )
    store.put(artifact)
    inspector = RuntimeRunInspector(store)

    first = inspector.read_artifact_payload_page(
        artifact.descriptor.artifact_id, offset=0, max_bytes=4
    )
    second = inspector.read_artifact_payload_page(
        artifact.descriptor.artifact_id, offset=first.next_offset or 0, max_bytes=6
    )

    assert base64.b64decode(first.data_base64) == b"0123"
    assert first.next_offset == 4
    assert base64.b64decode(second.data_base64) == b"456789"
    assert second.next_offset is None
    assert first.payload_sha256 == second.payload_sha256

    with pytest.raises(ValueError, match="between 1 and 65536"):
        inspector.read_artifact_payload_page(
            artifact.descriptor.artifact_id, max_bytes=65_537
        )
