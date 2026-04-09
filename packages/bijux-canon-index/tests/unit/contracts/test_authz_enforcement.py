# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_canon_index.contracts.authz import AllowAllAuthz, DenyAllAuthz
from bijux_canon_index.core.errors import AuthzDeniedError
from bijux_canon_index.infra.adapters.memory.backend import memory_backend
import pytest


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
