# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Mapping, MutableMapping
from dataclasses import replace
import hashlib
import json
from pathlib import Path
from typing import cast

import pytest

from bijux_canon_index.application import (
    CitationResolutionBatch,
    CitationRetrievalMode,
    DenseCandidateBatch,
    DenseCandidateMode,
    DenseCandidateOutcome,
    LexicalCandidateBatch,
    LexicalCandidateOutcome,
    RetrievalTraceArtifact,
    RetrievalTraceDriftKind,
    RetrievalTraceReplayInput,
    RetrievalTraceReplayOutcome,
    RetrievalTraceStore,
    RrfFusionBatch,
    VexPolicyDecision,
    VexPolicyStatus,
    build_retrieval_trace,
    compare_retrieval_traces,
    replay_retrieval_trace,
)

_GENERATION_ID = "sha256:generation"
_MODEL_ID = "sha256:model"
_QUERY = "ancient dna"
_QUERY_SHA = hashlib.sha256(_QUERY.encode()).hexdigest()


def _request(mode: CitationRetrievalMode) -> dict[str, object]:
    return {
        "candidate_limit": 20,
        "generation_id": _GENERATION_ID,
        "query_text": _QUERY,
        "query_text_sha256": _QUERY_SHA,
        "retrieval_mode": mode.value,
        "top_k": 10,
    }


def _artifact(
    *,
    mode: CitationRetrievalMode = CitationRetrievalMode.lexical,
    timing: float = 1.0,
    final_text: str = "evidence",
    attempt_marker: str = "a",
) -> RetrievalTraceArtifact:
    return RetrievalTraceArtifact(
        request=_request(mode),
        generation_id=_GENERATION_ID,
        model_lock_artifact_id=_MODEL_ID,
        retrieval_mode=mode,
        filters={"languages": ["en"]},
        candidates={
            "lexical": [
                {
                    "artifact_id": "sha256:" + attempt_marker * 64,
                    "chunk_id": "chunk-a",
                    "rank": 1,
                }
            ]
        },
        fusion={},
        selection={},
        rerank={},
        final_hits=(
            {
                "artifact_id": "sha256:" + attempt_marker * 64,
                "chunk_id": "chunk-a",
                "channels": [
                    {
                        "execution_artifact_id": "sha256:" + attempt_marker * 64,
                    }
                ],
                "rank": 1,
                "verbatim_text": final_text,
            },
        ),
        timings_ms={"total": timing},
        policy_decisions={"lexical": [{"disposition": "included"}]},
    )


def _stored_path(root: Path, artifact_id: str) -> Path:
    digest = artifact_id.removeprefix("sha256:")
    return root / "objects" / "sha256" / digest[:2] / f"{digest}.json"


def test_trace_store_survives_restart_and_inspects_all_components(
    tmp_path: Path,
) -> None:
    artifact = _artifact()
    stored = RetrievalTraceStore(tmp_path).put(artifact)

    restarted = RetrievalTraceStore(tmp_path)
    loaded = restarted.load(artifact.artifact_id)
    inspection = restarted.inspect(artifact.artifact_id)

    assert loaded == stored
    assert loaded.record["request"] == _request(CitationRetrievalMode.lexical)
    assert loaded.record["filters"] == {"languages": ["en"]}
    assert loaded.record["candidates"]
    assert loaded.record["policy_decisions"]
    assert inspection.execution_id == artifact.execution_id
    assert inspection.final_hit_count == 1
    assert set(inspection.component_hashes) == {
        "candidates",
        "filters",
        "final_hits",
        "fusion",
        "policy_decisions",
        "request",
        "rerank",
        "selection",
        "timings_ms",
    }


def test_trace_replay_ignores_timing_but_compares_semantic_outputs(
    tmp_path: Path,
) -> None:
    store = RetrievalTraceStore(tmp_path)
    original = _artifact(timing=1.0)
    store.put(original)
    observed: dict[str, Mapping[str, object]] = {}

    def execute(replay_input: RetrievalTraceReplayInput) -> RetrievalTraceArtifact:
        observed["request"] = replay_input.request
        with pytest.raises(TypeError):
            cast(MutableMapping[str, object], replay_input.request)["top_k"] = 99
        return _artifact(timing=2.0, attempt_marker="b")

    comparison = replay_retrieval_trace(store, original.artifact_id, execute)

    assert observed["request"]["query_text"] == _QUERY
    assert comparison.outcome is RetrievalTraceReplayOutcome.exact_match
    assert comparison.original_artifact_id != comparison.replay_artifact_id
    assert comparison.changed_components == ()


def test_trace_comparison_refuses_input_drift_and_reports_output_divergence(
    tmp_path: Path,
) -> None:
    store = RetrievalTraceStore(tmp_path)
    original = store.put(_artifact())
    drifted_request = _request(CitationRetrievalMode.lexical)
    drifted_request["query_text"] = "different"
    drifted_request["query_text_sha256"] = hashlib.sha256(b"different").hexdigest()
    drifted = store.put(replace(_artifact(), request=drifted_request))
    changed = store.put(_artifact(final_text="counterevidence"))

    refused = compare_retrieval_traces(original, drifted)
    diverged = compare_retrieval_traces(original, changed)

    assert refused.outcome is RetrievalTraceReplayOutcome.refused
    assert refused.drifts == (RetrievalTraceDriftKind.request,)
    assert diverged.outcome is RetrievalTraceReplayOutcome.diverged
    assert diverged.changed_components == ("final_hits",)


def test_trace_store_rejects_tampering_and_invalid_addresses(tmp_path: Path) -> None:
    store = RetrievalTraceStore(tmp_path)
    artifact = _artifact()
    store.put(artifact)
    path = _stored_path(tmp_path, artifact.artifact_id)
    record = json.loads(path.read_text())
    record["timings_ms"]["total"] = 999
    path.write_text(json.dumps(record, sort_keys=True, separators=(",", ":")) + "\n")

    with pytest.raises(ValueError, match="content address"):
        store.load(artifact.artifact_id)
    with pytest.raises(ValueError, match="content-addressed"):
        store.load("not-an-artifact")


def _lexical() -> LexicalCandidateBatch:
    return LexicalCandidateBatch(
        "bijux.canon.retrieval.lexical_candidates.v1",
        _GENERATION_ID,
        "sha256:lexical",
        "a" * 64,
        _QUERY_SHA,
        "b" * 64,
        10,
        20,
        LexicalCandidateOutcome.no_matches,
        (),
    )


def _dense(mode: DenseCandidateMode) -> DenseCandidateBatch:
    return DenseCandidateBatch(
        "bijux.canon.retrieval.dense_candidates.v1",
        _GENERATION_ID,
        _MODEL_ID,
        _QUERY_SHA,
        "c" * 64,
        mode,
        10,
        20,
        DenseCandidateOutcome.no_matches,
        (),
        "sha256:" + "d" * 64,
        "sha256:" + "e" * 64,
        "sha256:" + "f" * 64,
        VexPolicyDecision(
            "bijux.canon.vex.policy_decision.v1",
            VexPolicyStatus.admitted,
            (),
        ),
    )


def _fusion() -> RrfFusionBatch:
    return RrfFusionBatch(
        "bijux.canon.retrieval.rrf_fusion.v1",
        _GENERATION_ID,
        _QUERY_SHA,
        "1" * 64,
        "2" * 64,
        (),
    )


def _citations(mode: CitationRetrievalMode) -> CitationResolutionBatch:
    return CitationResolutionBatch(
        "bijux.canon.retrieval.citation_resolution.v1",
        _GENERATION_ID,
        "sha256:snapshot",
        _QUERY_SHA,
        mode,
        "sha256:" + "3" * 64,
        (),
    )


@pytest.mark.parametrize(
    ("mode", "lexical", "dense", "fusion"),
    [
        (CitationRetrievalMode.lexical, True, None, False),
        (CitationRetrievalMode.dense_exact, False, DenseCandidateMode.exact, False),
        (
            CitationRetrievalMode.local_hybrid_exact,
            True,
            DenseCandidateMode.exact,
            True,
        ),
        (
            CitationRetrievalMode.local_hybrid_ann,
            True,
            DenseCandidateMode.ann,
            True,
        ),
    ],
)
def test_trace_builder_links_every_retrieval_mode(
    mode: CitationRetrievalMode,
    lexical: bool,
    dense: DenseCandidateMode | None,
    fusion: bool,
) -> None:
    artifact = build_retrieval_trace(
        request=_request(mode),
        generation_id=_GENERATION_ID,
        model_lock_artifact_id=_MODEL_ID,
        retrieval_mode=mode,
        filters={},
        lexical=_lexical() if lexical else None,
        dense=_dense(dense) if dense else None,
        fusion=_fusion() if fusion else None,
        citations=_citations(mode),
        timings_ms={"total": 0.1},
    )

    assert artifact.retrieval_mode is mode
    assert artifact.execution_id.startswith("sha256:")
    assert artifact.component_hashes["candidates"]


def test_trace_builder_refuses_cross_mode_and_identity_drift() -> None:
    with pytest.raises(ValueError, match="mode differs"):
        build_retrieval_trace(
            request=_request(CitationRetrievalMode.dense_exact),
            generation_id=_GENERATION_ID,
            model_lock_artifact_id=_MODEL_ID,
            retrieval_mode=CitationRetrievalMode.dense_exact,
            filters={},
            dense=_dense(DenseCandidateMode.ann),
            citations=_citations(CitationRetrievalMode.dense_exact),
            timings_ms={"total": 0.1},
        )
    with pytest.raises(ValueError, match="query identity"):
        build_retrieval_trace(
            request=_request(CitationRetrievalMode.lexical),
            generation_id=_GENERATION_ID,
            model_lock_artifact_id=_MODEL_ID,
            retrieval_mode=CitationRetrievalMode.lexical,
            filters={},
            lexical=replace(_lexical(), query_text_sha256="0" * 64),
            citations=_citations(CitationRetrievalMode.lexical),
            timings_ms={"total": 0.1},
        )


def test_trace_values_reject_bad_query_timing_and_final_ranks() -> None:
    with pytest.raises(ValueError, match="query text identity"):
        replace(
            _artifact(),
            request={
                **_request(CitationRetrievalMode.lexical),
                "query_text_sha256": "0" * 64,
            },
        )
    with pytest.raises(ValueError, match="timings"):
        replace(_artifact(), timings_ms={"total": float("nan")})
    with pytest.raises(ValueError, match="contiguous"):
        replace(_artifact(), final_hits=({"chunk_id": "chunk-a", "rank": 2},))
