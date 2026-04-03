# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations
import pytest

from bijux_vex.core.types import Document
from tests.conformance.suite import default_backends, parametrize_backends


@parametrize_backends(default_backends())
def test_mid_tx_failure_rolls_back(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="fail-doc", text="temp")
    with pytest.raises(RuntimeError):
        with fixture.tx_factory() as tx:
            fixture.stores.vectors.put_document(tx, doc)
            raise RuntimeError("boom")
    assert fixture.stores.vectors.get_document(doc.document_id) is None


@parametrize_backends(default_backends())
def test_double_commit_is_idempotent(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="double", text="ok")
    tx = fixture.tx_factory()
    fixture.stores.vectors.put_document(tx, doc)
    tx.commit()
    tx.commit()  # should be no-op
    assert fixture.stores.vectors.get_document(doc.document_id) == doc


@parametrize_backends(default_backends())
def test_abort_after_stage_discards_changes(backend_case):
    fixture = backend_case.factory()
    doc = Document(document_id="abort-doc", text="temp")
    tx = fixture.tx_factory()
    fixture.stores.vectors.put_document(tx, doc)
    tx.abort()
    assert fixture.stores.vectors.get_document(doc.document_id) is None
