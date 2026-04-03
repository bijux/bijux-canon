# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

import hypothesis.strategies as st
from hypothesis import given, settings

from bijux_rag.core.rag_types import RawDoc
from bijux_rag.domain.capabilities import StorageRead
from bijux_rag.domain.effects.io_plan import IOPlan, io_delay, io_map, perform
from bijux_rag.infra.adapters.memory_storage import InMemoryStorage
from bijux_rag.result.types import Ok

settings.register_profile("ci", max_examples=100, derandomize=True, deadline=None)
settings.load_profile("ci")


def legacy_count_ok_docs(storage: StorageRead, path: str) -> int:
    return sum(1 for r in storage.read_docs(path) if isinstance(r, Ok))


def count_ok_docs_plan(storage: StorageRead, path: str) -> IOPlan[int]:
    # Migration pattern: keep core logic pure, lift the boundary call into IOPlan.
    return io_map(
        io_delay(lambda: Ok(storage.read_docs(path))),
        lambda it: sum(1 for r in it if isinstance(r, Ok)),
    )


@st.composite
def raw_doc(draw) -> RawDoc:
    # Avoid surrogates for predictable test output.
    safe_text = st.text(
        alphabet=st.characters(blacklist_categories=("Cs",), blacklist_characters=["\x00"]),
        max_size=50,
    )
    return RawDoc(
        doc_id=draw(safe_text.filter(bool)),
        title=draw(safe_text),
        abstract=draw(safe_text),
        categories=draw(safe_text),
    )


@given(docs=st.lists(raw_doc(), max_size=25))
def test_io_plan_migration_preserves_observable_result(docs: list[RawDoc]) -> None:
    storage = InMemoryStorage(preload={"in.csv": docs})
    legacy = legacy_count_ok_docs(storage, "in.csv")
    planned = perform(count_ok_docs_plan(storage, "in.csv"))
    assert planned == Ok(legacy)
