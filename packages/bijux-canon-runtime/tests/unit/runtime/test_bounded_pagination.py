from __future__ import annotations

from pathlib import Path

import pytest

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
