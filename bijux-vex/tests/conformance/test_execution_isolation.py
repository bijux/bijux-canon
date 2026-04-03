# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
from bijux_vex.infra.adapters.memory.backend import memory_backend
from bijux_vex.core.types import Document


def test_backends_are_isolated():
    a = memory_backend()
    b = memory_backend()
    assert a is not b
    assert a.stores.vectors.list_documents() == []
    assert b.stores.vectors.list_documents() == []

    with a.tx_factory() as tx:
        a.stores.vectors.put_document(tx, Document(document_id="a", text="A"))

    assert [d.document_id for d in a.stores.vectors.list_documents()] == ["a"]
    assert list(b.stores.vectors.list_documents()) == []
