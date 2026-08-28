# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import pytest

from bijux_canon_index.application import retrieval_filter_capability
from bijux_canon_index.domain.metadata_filters import (
    GOVERNED_METADATA_FIELDS,
    MetadataOperator,
)


@pytest.mark.parametrize("backend", ["sqlite-fts5", "faiss-flat-ip", "faiss-hnsw"])
def test_local_backends_declare_equivalent_pre_limit_filter_contract(
    backend: str,
) -> None:
    capability = retrieval_filter_capability(backend)

    assert capability.enforcement_stage == "query_time_before_result_limit"
    assert capability.result_limit_applied_after_filter
    assert capability.governed_fields == GOVERNED_METADATA_FIELDS
    assert capability.user_operators == tuple(
        operator.value for operator in MetadataOperator
    )
    assert capability.limitations


def test_unknown_filter_backend_is_refused() -> None:
    with pytest.raises(ValueError, match="unsupported"):
        retrieval_filter_capability("remote-unknown")
