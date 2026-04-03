# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.contracts.authz import AllowAllAuthz, DenyAllAuthz
from bijux_vex.core.errors import AuthzDeniedError
from bijux_vex.infra.adapters.memory.backend import memory_backend


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
