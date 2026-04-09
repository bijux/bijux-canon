# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""End-to-end tests for the application API surface."""

from __future__ import annotations

from bijux_canon_ingest import (
    DEFAULT_RULES,
    All,
    Err,
    IngestBoundaryDeps,
    IngestConfig,
    LenGt,
    Ok,
    StartsWith,
    build_ingest_deps,
    clean_doc,
    embed_chunk,
    eval_pred,
    gen_chunk_doc,
    iter_ingest_pipeline_core,
    parse_ingest_config,
    parse_rule,
    run_ingest_pipeline_docs,
    run_ingest_pipeline_path,
    structural_dedup_chunks,
)
from bijux_canon_ingest.core.rules_lint import assert_rule_is_safe_expr
from bijux_canon_ingest.core.types import RagEnv, RawDoc
from bijux_canon_ingest.result import Result
from hypothesis import given
import pytest
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
    config = IngestConfig(env=env, keep=DEFAULT_RULES)
    deps = build_ingest_deps(config)
    chunks, obs = run_ingest_pipeline_docs(docs, config, deps)
    assert chunks == _baseline_chunks(docs, env)
    assert obs.total_docs == len(docs)
    assert obs.total_chunks == len(chunks)


@given(docs=doc_list_strategy(), env=env_strategy())
def test_iter_rag_core_deterministic(docs: list[RawDoc], env: RagEnv) -> None:
    config = IngestConfig(env=env)
    deps = build_ingest_deps(config)
    out1 = list(iter_ingest_pipeline_core(docs, config, deps))
    out2 = list(iter_ingest_pipeline_core(docs, config, deps))
    assert out1 == out2


@given(docs=doc_list_strategy(), env=env_strategy())
def test_full_rag_api_path_boundary_shape(docs: list[RawDoc], env: RagEnv) -> None:
    config = IngestConfig(env=env)
    deps = IngestBoundaryDeps(core=build_ingest_deps(config), reader=FakeReader(docs))
    res = run_ingest_pipeline_path("fake.csv", config, deps)
    assert isinstance(res, Ok)
    chunks, obs = res.value
    assert chunks == _baseline_chunks(docs, env)
    assert obs.total_docs == len(docs)


def test_parse_ingest_config_rejects_unknown_rule() -> None:
    res = parse_ingest_config({"chunk_size": 256, "clean_rules": ["nope"]})
    assert isinstance(res, Err)


def test_parse_rule_lints_unsafe_expr() -> None:
    with pytest.raises(ValueError, match="Forbidden"):
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
