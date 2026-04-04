# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from types import SimpleNamespace

from bijux_canon_index.application.orchestration.result_records import (
    artifact_build_params,
    metadata_tuple,
)


def test_artifact_build_params_reads_vector_store_metadata() -> None:
    stores = SimpleNamespace(
        vectors=SimpleNamespace(
            vector_store_metadata={
                "backend": "qdrant",
                "uri_redacted": "qdrant://redacted",
                "index_params": {"m": 16},
            }
        )
    )

    assert artifact_build_params(vector_store_enabled=True, stores=stores) == (
        ("vector_store.backend", "qdrant"),
        ("vector_store.uri_redacted", "qdrant://redacted"),
        ("vector_store.index_params", "{'m': 16}"),
    )


def test_metadata_tuple_omits_none_values() -> None:
    assert metadata_tuple({"provider": "test", "seed": None}) == (("provider", "test"),)
