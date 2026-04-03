# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

"""End-to-end tests for the Bijux RAG API surface."""

from __future__ import annotations

import pytest
from hypothesis import given

from bijux_rag import (
    DEFAULT_RULES,
    All,
    Err,
    LenGt,
    Ok,
    RagBoundaryDeps,
    RagConfig,
    StartsWith,
    boundary_rag_config,
    clean_doc,
    embed_chunk,
    eval_pred,
    full_rag_api_docs,
    full_rag_api_path,
    gen_chunk_doc,
    get_deps,
    iter_rag_core,
    parse_rule,
    structural_dedup_chunks,
)
from bijux_rag.core.rag_types import RagEnv, RawDoc
from bijux_rag.core.rules_lint import assert_rule_is_safe_expr
from bijux_rag.result import Result
from tests.strategies import doc_list_strategy, env_strategy


def _baseline_chunks(docs: list[RawDoc], env: RagEnv) -> list:
    cleaned = [clean_doc(d) for d in docs]
    embedded = [embed_chunk(c) for cd in cleaned for c in gen_chunk_doc(cd, env)]
    return structural_dedup_chunks(embedded)


class FakeReader:
    def __init__(self, docs: list[RawDoc]) -> None:
        self._docs = docs

    def read_docs(self, path: str) -> Result[list[RawDoc], str]:
        _ = path
        return Ok(self._docs)


@given(docs=doc_list_strategy(), env=env_strategy())
def test_full_rag_api_docs_matches_baseline(docs: list[RawDoc], env: RagEnv) -> None:
    config = RagConfig(env=env, keep=DEFAULT_RULES)
    deps = get_deps(config)
    chunks, obs = full_rag_api_docs(docs, config, deps)
    assert chunks == _baseline_chunks(docs, env)
    assert obs.total_docs == len(docs)
    assert obs.total_chunks == len(chunks)


@given(docs=doc_list_strategy(), env=env_strategy())
def test_iter_rag_core_deterministic(docs: list[RawDoc], env: RagEnv) -> None:
    config = RagConfig(env=env)
    deps = get_deps(config)
    out1 = list(iter_rag_core(docs, config, deps))
    out2 = list(iter_rag_core(docs, config, deps))
    assert out1 == out2


@given(docs=doc_list_strategy(), env=env_strategy())
def test_full_rag_api_path_boundary_shape(docs: list[RawDoc], env: RagEnv) -> None:
    config = RagConfig(env=env)
    deps = RagBoundaryDeps(core=get_deps(config), reader=FakeReader(docs))
    res = full_rag_api_path("fake.csv", config, deps)
    assert isinstance(res, Ok)
    chunks, obs = res.value
    assert chunks == _baseline_chunks(docs, env)
    assert obs.total_docs == len(docs)


def test_boundary_rag_config_rejects_unknown_rule() -> None:
    res = boundary_rag_config({"chunk_size": 256, "clean_rules": ["nope"]})
    assert isinstance(res, Err)


def test_parse_rule_lints_unsafe_expr() -> None:
    with pytest.raises(ValueError):
        assert_rule_is_safe_expr("__import__('os').system('echo nope')")


def test_parse_rule_executes_safe_expr() -> None:
    rule = parse_rule('d.categories.startswith("cs.") and len(d.abstract) > 0')
    assert rule(RawDoc("1", "t", "a", "cs.AI"))
    assert not rule(RawDoc("1", "t", "a", "math.NT"))


def test_pred_dsl_eval_pred() -> None:
    pred = All((StartsWith("categories", "cs."), LenGt("abstract", 1)))
    doc_ok = RawDoc("1", "t", "abc", "cs.AI")
    doc_bad = RawDoc("1", "t", "a", "cs.AI")
    assert eval_pred(doc_ok, pred)
    assert not eval_pred(doc_bad, pred)
