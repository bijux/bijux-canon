# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
# SPDX-License-Identifier: Apache-2.0
from __future__ import annotations
import pytest

from bijux_canon_index.core.types import Document
from tests.conformance.suite import default_backends, parametrize_backends


@parametrize_backends(default_backends())
def test_abort_rolls_back_changes(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="doc-tx", text="temp")

    with pytest.raises(RuntimeError):
        with fixture.tx_factory() as tx:
            fixture.authz.check(
                tx, action="put_document", resource="document", actor="tester"
            )
            fixture.stores.vectors.put_document(tx, doc)
            raise RuntimeError("force abort")

    assert fixture.stores.vectors.get_document(doc.document_id) is None
