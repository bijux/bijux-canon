# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

import pytest

from bijux_canon_index.contracts.authz import (
    AllowAllAuthz,
    DenyAllAuthz,
    RetrievalAuthorizationScope,
    authorize_retrieval_filter,
)
from bijux_canon_index.core.errors import AuthzDeniedError
from bijux_canon_index.domain.metadata_filters import MetadataFilter
from bijux_canon_index.infra.adapters.memory.backend import memory_backend


def test_deny_all_blocks_mutations() -> None:
    backend = memory_backend()
    deny = DenyAllAuthz()
    with backend.tx_factory() as tx:
        with pytest.raises(AuthzDeniedError):
            deny.check(tx, action="put_document", resource="document")
        deny.check(tx, action="get_document", resource="document")


def test_allow_all_remains_permissive() -> None:
    backend = memory_backend()
    allow = AllowAllAuthz()
    with backend.tx_factory() as tx:
        allow.check(tx, action="put_document", resource="document")


def test_retrieval_authority_constrains_an_unfiltered_request() -> None:
    scope = RetrievalAuthorizationScope(
        generation_ids=("generation-a",),
        source_ids=("source-b", "source-a", "source-a"),
        actor="researcher",
    )

    effective = authorize_retrieval_filter(
        scope,
        generation_id="generation-a",
        requested=None,
    )

    assert effective == MetadataFilter(source_ids=("source-a", "source-b"))
    assert scope.source_ids == ("source-a", "source-b")
    assert scope.artifact_id.startswith("sha256:")


def test_retrieval_authority_rejects_generation_widening() -> None:
    scope = RetrievalAuthorizationScope(
        generation_ids=("generation-a",),
        source_ids=("source-a",),
        paths=("inside/article.xml",),
    )

    with pytest.raises(AuthzDeniedError):
        authorize_retrieval_filter(
            scope,
            generation_id="generation-b",
            requested=None,
        )


def test_retrieval_authority_turns_disjoint_source_requests_into_match_none() -> None:
    scope = RetrievalAuthorizationScope(
        generation_ids=("generation-a",),
        source_ids=("source-a",),
    )

    effective = authorize_retrieval_filter(
        scope,
        generation_id="generation-a",
        requested=MetadataFilter(source_ids=("source-b",)),
    )

    assert effective is not None
    assert effective.match_none
    assert effective.source_ids == ()
