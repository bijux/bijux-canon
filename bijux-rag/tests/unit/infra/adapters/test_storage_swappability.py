# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import csv
import os
import tempfile

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.infra.adapters.file_storage import FileStorage
from bijux_rag.infra.adapters.memory_storage import InMemoryStorage
from bijux_rag.result.types import Ok

settings.register_profile("ci", max_examples=100, derandomize=True, deadline=None)
settings.load_profile("ci")


def _csv_safe_text(max_size: int) -> st.SearchStrategy[str]:
    # Avoid surrogates (not UTF-8 encodable) for filesystem roundtrips.
    return st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters=["\x00"]),
        max_size=max_size,
    )


@st.composite
def _csv_safe_raw_doc(draw) -> RawDoc:
    return RawDoc(
        doc_id=draw(_csv_safe_text(20).filter(bool)),
        title=draw(_csv_safe_text(100)),
        abstract=draw(_csv_safe_text(500)),
        categories=draw(_csv_safe_text(50)),
    )


@given(docs=st.lists(_csv_safe_raw_doc(), max_size=25))
def test_storage_read_docs_swappability_file_vs_memory(docs: list[RawDoc]) -> None:
    mem = InMemoryStorage(preload={"in.csv": docs})
    mem_results = list(mem.read_docs("in.csv"))

    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "in.csv")
        with open(path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["doc_id", "title", "abstract", "categories"])
            writer.writeheader()
            for d in docs:
                writer.writerow(
                    {
                        "doc_id": d.doc_id,
                        "title": d.title,
                        "abstract": d.abstract,
                        "categories": d.categories,
                    }
                )

        file_results = list(FileStorage().read_docs(path))

    assert file_results == [Ok(d) for d in docs]
    assert file_results == mem_results
