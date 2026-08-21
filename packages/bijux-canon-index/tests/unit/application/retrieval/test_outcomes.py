# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("faiss")

from bijux_canon_index.application import (
    AdmittedIndexChunk,
    IndexBuildLimits,
    IndexCompatibility,
    IndexService,
    LexicalCandidateService,
    RetrievalChannel,
    RetrievalChannelResult,
    RetrievalChannelState,
    RetrievalEvidenceReference,
    RetrievalIssueCode,
    RetrievalMode,
    RetrievalOutcomeService,
    RetrievalOutcomeStatus,
)
from bijux_canon_index.application.index_generation import LEXICAL_NAME
from bijux_canon_index.infra.adapters.faiss.hnsw import HnswParameters
from bijux_canon_index.infra.embeddings.remote.contracts import RemoteEmbeddingError


def _registry(tmp_path: Path) -> tuple[Path, str, IndexCompatibility]:
    root = tmp_path / "registry"
    compatibility = IndexCompatibility("sha256:model", 3)
    report = IndexService(root, compatibility=compatibility).build(
        (
            AdmittedIndexChunk(
                "chunk-a",
                "paper-a",
                0,
                "Ancient DNA preserves direct evidence.",
                (1.0, 0.0, 0.0),
                {"source_id": "paper-a", "language": "en"},
            ),
        ),
        snapshot_artifact_id="sha256:snapshot",
        model_lock_artifact_id="sha256:model",
        limits=IndexBuildLimits(10, 10_000, 10_000, 10_000),
        hnsw_parameters=HnswParameters(m=2, ef_construction=8, ef_search=8),
        activate=True,
    )
    return root, report.generation_id, compatibility


def _evidence() -> RetrievalEvidenceReference:
    return RetrievalEvidenceReference(
        chunk_id="chunk-a",
        document_id="paper-a",
        ordinal=0,
        source_text_sha256="a" * 64,
    )


def _result(
    channel: RetrievalChannel,
    generation_id: str,
    *,
    state: RetrievalChannelState = RetrievalChannelState.available,
) -> RetrievalChannelResult:
    return RetrievalChannelResult(
        channel=channel,
        generation_id=generation_id,
        state=state,
        evidence=(_evidence(),) if state is RetrievalChannelState.available else (),
    )


@pytest.mark.parametrize(
    ("mode", "channels"),
    (
        (RetrievalMode.lexical, (RetrievalChannel.lexical,)),
        (RetrievalMode.dense_exact, (RetrievalChannel.dense,)),
        (
            RetrievalMode.local_hybrid_exact,
            (RetrievalChannel.lexical, RetrievalChannel.dense),
        ),
        (
            RetrievalMode.local_hybrid_ann,
            (RetrievalChannel.lexical, RetrievalChannel.dense),
        ),
    ),
)
def test_complete_modes_return_only_observed_evidence(
    tmp_path: Path,
    mode: RetrievalMode,
    channels: tuple[RetrievalChannel, ...],
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    service = RetrievalOutcomeService(root, compatibility=compatibility)

    outcome = service.execute(
        mode=mode,
        generation_id=generation_id,
        channel_runners={
            channel: lambda channel=channel: _result(channel, generation_id)
            for channel in channels
        },
    )

    assert outcome.status is RetrievalOutcomeStatus.success
    assert outcome.usable
    assert outcome.evidence == (_evidence(),)
    assert outcome.issues == ()
    assert outcome.outcome_id.startswith("sha256:")


@pytest.mark.parametrize("mode", tuple(RetrievalMode))
def test_empty_modes_return_typed_no_hits_without_evidence(
    tmp_path: Path,
    mode: RetrievalMode,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=mode,
        generation_id=generation_id,
        channel_runners={
            channel: lambda channel=channel: _result(
                channel,
                generation_id,
                state=RetrievalChannelState.empty,
            )
            for channel in mode.required_channels
        },
    )

    assert outcome.status is RetrievalOutcomeStatus.insufficient
    assert [issue.code for issue in outcome.issues] == [RetrievalIssueCode.no_hits]
    assert outcome.evidence == ()


@pytest.mark.parametrize(
    "mode", (RetrievalMode.local_hybrid_exact, RetrievalMode.local_hybrid_ann)
)
def test_sparse_hybrid_results_fail_closed(
    tmp_path: Path,
    mode: RetrievalMode,
) -> None:
    root, generation_id, compatibility = _registry(tmp_path)

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=mode,
        generation_id=generation_id,
        channel_runners={
            RetrievalChannel.lexical: lambda: _result(
                RetrievalChannel.lexical, generation_id
            ),
            RetrievalChannel.dense: lambda: _result(
                RetrievalChannel.dense,
                generation_id,
                state=RetrievalChannelState.empty,
            ),
        },
    )

    assert outcome.status is RetrievalOutcomeStatus.insufficient
    assert outcome.issues[0].code is RetrievalIssueCode.sparse_results
    assert outcome.channels[0].evidence == (_evidence(),)
    assert outcome.evidence == ()


def test_missing_hybrid_channel_is_explicit(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=RetrievalMode.local_hybrid_exact,
        generation_id=generation_id,
        channel_runners={
            RetrievalChannel.lexical: lambda: _result(
                RetrievalChannel.lexical, generation_id
            )
        },
    )

    assert outcome.status is RetrievalOutcomeStatus.insufficient
    assert outcome.issues[0].code is RetrievalIssueCode.missing_channel
    assert outcome.issues[0].channels == (RetrievalChannel.dense,)
    assert outcome.evidence == ()


def test_stale_generation_is_rejected_before_channels_run(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    calls = 0

    def runner() -> RetrievalChannelResult:
        nonlocal calls
        calls += 1
        return _result(RetrievalChannel.lexical, generation_id)

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=RetrievalMode.lexical,
        generation_id="sha256:" + "b" * 64,
        channel_runners={RetrievalChannel.lexical: runner},
    )

    assert outcome.status is RetrievalOutcomeStatus.integrity_error
    assert outcome.issues[0].code is RetrievalIssueCode.stale_generation
    assert outcome.active_generation_id == generation_id
    assert calls == 0
    assert outcome.evidence == ()


def test_corrupt_segment_is_typed_without_exception_detail(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)
    lexical_path = (
        root / "generations" / generation_id.removeprefix("sha256:") / LEXICAL_NAME
    )
    with lexical_path.open("r+b") as handle:
        handle.seek(0)
        handle.write(b"corrupt!")

    def corrupt_runner() -> RetrievalChannelResult:
        return RetrievalChannelResult.from_lexical(
            LexicalCandidateService(root, compatibility=compatibility).generate(
                "ancient DNA",
                generation_id=generation_id,
                top_k=1,
                candidate_limit=1,
            )
        )

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=RetrievalMode.lexical,
        generation_id=generation_id,
        channel_runners={RetrievalChannel.lexical: corrupt_runner},
    )

    assert outcome.status is RetrievalOutcomeStatus.integrity_error
    assert outcome.issues[0].code is RetrievalIssueCode.corrupt_segment
    assert outcome.issues[0].error_type == "IndexGenerationIntegrityError"
    assert "corrupt" not in outcome.outcome_id
    assert outcome.evidence == ()


def test_partial_provider_failure_is_sanitized_and_retryable(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)

    def provider_failure() -> RetrievalChannelResult:
        raise RemoteEmbeddingError(
            "credential=must-not-escape",
            category="timeout",
            retryable=True,
            attempts=3,
        )

    outcome = RetrievalOutcomeService(root, compatibility=compatibility).execute(
        mode=RetrievalMode.local_hybrid_ann,
        generation_id=generation_id,
        channel_runners={
            RetrievalChannel.lexical: lambda: _result(
                RetrievalChannel.lexical, generation_id
            ),
            RetrievalChannel.dense: provider_failure,
        },
    )

    assert outcome.status is RetrievalOutcomeStatus.dependency_error
    assert outcome.issues[0].code is RetrievalIssueCode.provider_failure
    assert outcome.issues[0].retryable
    assert outcome.issues[0].error_type == "RemoteEmbeddingError"
    assert "credential" not in repr(outcome)
    assert outcome.evidence == ()


def test_unknown_runner_errors_are_not_misclassified(tmp_path: Path) -> None:
    root, generation_id, compatibility = _registry(tmp_path)

    def programming_error() -> RetrievalChannelResult:
        raise TypeError("broken adapter")

    with pytest.raises(TypeError, match="broken adapter"):
        RetrievalOutcomeService(root, compatibility=compatibility).execute(
            mode=RetrievalMode.lexical,
            generation_id=generation_id,
            channel_runners={RetrievalChannel.lexical: programming_error},
        )
