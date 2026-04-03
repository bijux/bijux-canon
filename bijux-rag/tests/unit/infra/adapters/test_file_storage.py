# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import builtins
from io import StringIO

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.infra.adapters.file_storage import FileStorage
from bijux_rag.result.types import Err, Ok


def test_file_storage_read_docs_partial_consumption_closes_file(monkeypatch) -> None:
    f = StringIO("doc_id,title,abstract,categories\n1,T,A,C\n2,T2,A2,C2\n")
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: f)

    storage = FileStorage()
    it = storage.read_docs("ignored.csv")
    first = next(it)
    assert first == Ok(RawDoc(doc_id="1", title="T", abstract="A", categories="C"))
    assert f.closed is False
    it.close()
    assert f.closed is True


def test_file_storage_read_docs_parse_error_yields_err(monkeypatch) -> None:
    # Missing required fields for RawDoc -> TypeError -> PARSE_ROW.
    f = StringIO("doc_id,title\n1,T\n")
    monkeypatch.setattr(builtins, "open", lambda *args, **kwargs: f)

    storage = FileStorage()
    it = storage.read_docs("ignored.csv")
    first = next(it)
    assert isinstance(first, Err)
    assert first.error.code == "PARSE_ROW"
