# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Fail-closed retrieval outcomes for unavailable or untrustworthy evidence."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import asdict, dataclass
from enum import StrEnum
import hashlib
import json
from pathlib import Path

from bijux_canon_index.application.index_activation import (
    IndexActivationError,
    IndexGenerationRegistry,
)
from bijux_canon_index.application.index_audit import (
    IndexCompatibility,
    IndexGenerationIncompatibleError,
)
from bijux_canon_index.application.index_generation import IndexGenerationIntegrityError
from bijux_canon_index.core.errors import BackendUnavailableError, CorruptArtifactError
from bijux_canon_index.infra.adapters.faiss.exact import (
    FaissExactIndexCorruptionError,
)
from bijux_canon_index.infra.adapters.faiss.hnsw import (
    FaissHnswIndexCorruptionError,
)
from bijux_canon_index.infra.adapters.sqlite.lexical import (
    LexicalIndexCorruptionError,
)
from bijux_canon_index.infra.embeddings.cache import EmbeddingCacheCorruptionError
from bijux_canon_index.infra.embeddings.remote.contracts import RemoteEmbeddingError

from .dense import DenseCandidateBatch, DenseCandidateMode, DenseCandidateOutcome
from .fusion import RetrievalChannel
from .lexical import LexicalCandidateBatch, LexicalCandidateOutcome


class RetrievalMode(StrEnum):
    """Installed retrieval profiles covered by the production contract."""

    lexical = "lexical"
    dense_exact = "dense-exact"
    local_hybrid_exact = "local-hybrid-exact"
    local_hybrid_ann = "local-hybrid-ann"

    @property
    def required_channels(self) -> tuple[RetrievalChannel, ...]:
        """Return channels that must all complete for this mode."""

        if self is RetrievalMode.lexical:
            return (RetrievalChannel.lexical,)
        if self is RetrievalMode.dense_exact:
            return (RetrievalChannel.dense,)
        return (RetrievalChannel.lexical, RetrievalChannel.dense)

    @property
    def dense_mode(self) -> DenseCandidateMode | None:
        """Return the dense backend required by this mode, when present."""

        if self in (RetrievalMode.dense_exact, RetrievalMode.local_hybrid_exact):
            return DenseCandidateMode.exact
        if self is RetrievalMode.local_hybrid_ann:
            return DenseCandidateMode.ann
        return None


class RetrievalChannelState(StrEnum):
    """Observed state of a required retrieval channel."""

    available = "available"
    empty = "empty"
    refused = "refused"
    unavailable = "unavailable"
    corrupt = "corrupt"


class RetrievalOutcomeStatus(StrEnum):
    """Whether evidence may be used by downstream reasoning."""

    success = "success"
    insufficient = "insufficient"
    integrity_error = "integrity_error"
    dependency_error = "dependency_error"
    policy_refused = "policy_refused"


class RetrievalIssueKind(StrEnum):
    """Stable category for operator and downstream policy decisions."""

    insufficiency = "insufficiency"
    integrity = "integrity"
    dependency = "dependency"
    policy = "policy"


class RetrievalIssueCode(StrEnum):
    """Stable reasons why a retrieval result cannot be used."""

    no_hits = "no_hits"
    sparse_results = "sparse_results"
    missing_channel = "missing_channel"
    stale_generation = "stale_generation"
    corrupt_segment = "corrupt_segment"
    provider_failure = "provider_failure"
    policy_refused = "policy_refused"


@dataclass(frozen=True, slots=True)
class RetrievalEvidenceReference:
    """One observed channel result bound to immutable source text."""

    chunk_id: str
    document_id: str
    ordinal: int
    source_text_sha256: str

    def __post_init__(self) -> None:
        if not self.chunk_id or not self.document_id:
            raise ValueError("retrieval evidence identities must not be empty")
        if self.ordinal < 0:
            raise ValueError("retrieval evidence ordinal must not be negative")
        if len(self.source_text_sha256) != 64 or any(
            value not in "0123456789abcdef" for value in self.source_text_sha256
        ):
            raise ValueError("retrieval evidence requires a lowercase SHA-256")


@dataclass(frozen=True, slots=True)
class RetrievalChannelResult:
    """Sanitized result of one generation-bound channel execution."""

    channel: RetrievalChannel
    generation_id: str
    state: RetrievalChannelState
    evidence: tuple[RetrievalEvidenceReference, ...] = ()
    error_type: str | None = None
    retryable: bool = False

    def __post_init__(self) -> None:
        if not isinstance(self.channel, RetrievalChannel):
            raise ValueError("retrieval result channel is unsupported")
        if not self.generation_id:
            raise ValueError("retrieval result generation must not be empty")
        if self.state is RetrievalChannelState.available and not self.evidence:
            raise ValueError("available retrieval channels require observed evidence")
        if self.state is not RetrievalChannelState.available and self.evidence:
            raise ValueError("unusable retrieval channels cannot expose evidence")
        if (
            self.state
            in (
                RetrievalChannelState.corrupt,
                RetrievalChannelState.unavailable,
            )
            and not self.error_type
        ):
            raise ValueError("failed retrieval channels require a sanitized error type")
        chunk_ids = tuple(item.chunk_id for item in self.evidence)
        if len(chunk_ids) != len(set(chunk_ids)):
            raise ValueError("retrieval channel evidence must be unique")

    @classmethod
    def from_lexical(cls, batch: LexicalCandidateBatch) -> RetrievalChannelResult:
        """Adapt a typed lexical batch without inventing evidence."""

        evidence = tuple(
            RetrievalEvidenceReference(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                ordinal=candidate.ordinal,
                source_text_sha256=candidate.source_text_sha256,
            )
            for candidate in batch.candidates
        )
        return cls(
            channel=RetrievalChannel.lexical,
            generation_id=batch.generation_id,
            state=(
                RetrievalChannelState.available
                if evidence
                else RetrievalChannelState.empty
            ),
            evidence=evidence,
        )

    @classmethod
    def from_dense(cls, batch: DenseCandidateBatch) -> RetrievalChannelResult:
        """Adapt an admitted, empty, or refused dense VEX batch."""

        if batch.outcome is DenseCandidateOutcome.refused:
            return cls(
                channel=RetrievalChannel.dense,
                generation_id=batch.generation_id,
                state=RetrievalChannelState.refused,
                error_type="VexPolicyRefusal",
            )
        evidence = tuple(
            RetrievalEvidenceReference(
                chunk_id=candidate.chunk_id,
                document_id=candidate.document_id,
                ordinal=candidate.ordinal,
                source_text_sha256=candidate.source_text_sha256,
            )
            for candidate in batch.candidates
        )
        return cls(
            channel=RetrievalChannel.dense,
            generation_id=batch.generation_id,
            state=(
                RetrievalChannelState.available
                if evidence
                else RetrievalChannelState.empty
            ),
            evidence=evidence,
        )


@dataclass(frozen=True, slots=True)
class RetrievalIssue:
    """One content-safe reason why evidence cannot be used."""

    kind: RetrievalIssueKind
    code: RetrievalIssueCode
    channels: tuple[RetrievalChannel, ...]
    retryable: bool = False
    error_type: str | None = None


@dataclass(frozen=True, slots=True)
class RetrievalOutcome:
    """Complete fail-closed outcome for one retrieval attempt."""

    schema_version: str
    outcome_id: str
    mode: RetrievalMode
    requested_generation_id: str
    active_generation_id: str | None
    status: RetrievalOutcomeStatus
    channels: tuple[RetrievalChannelResult, ...]
    issues: tuple[RetrievalIssue, ...]

    @property
    def usable(self) -> bool:
        """Return whether downstream reasoning may consume this outcome."""

        return self.status is RetrievalOutcomeStatus.success

    @property
    def evidence(self) -> tuple[RetrievalEvidenceReference, ...]:
        """Return observed evidence only for a complete successful result."""

        if not self.usable:
            return ()
        seen: set[str] = set()
        evidence = []
        for channel in self.channels:
            for reference in channel.evidence:
                if reference.chunk_id not in seen:
                    seen.add(reference.chunk_id)
                    evidence.append(reference)
        return tuple(evidence)


ChannelRunner = Callable[[], RetrievalChannelResult]


_CORRUPTION_ERRORS = (
    CorruptArtifactError,
    EmbeddingCacheCorruptionError,
    FaissExactIndexCorruptionError,
    FaissHnswIndexCorruptionError,
    IndexActivationError,
    IndexGenerationIncompatibleError,
    IndexGenerationIntegrityError,
    LexicalIndexCorruptionError,
)
_PROVIDER_ERRORS = (
    BackendUnavailableError,
    ConnectionError,
    RemoteEmbeddingError,
    TimeoutError,
)


def _outcome_id(payload: object) -> str:
    raw = json.dumps(
        payload,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )
    return f"sha256:{hashlib.sha256(raw.encode('utf-8')).hexdigest()}"


def _failed_channel(
    channel: RetrievalChannel,
    generation_id: str,
    error: Exception,
) -> RetrievalChannelResult:
    if isinstance(error, _CORRUPTION_ERRORS):
        state = RetrievalChannelState.corrupt
    elif isinstance(error, _PROVIDER_ERRORS):
        state = RetrievalChannelState.unavailable
    else:
        raise error
    return RetrievalChannelResult(
        channel=channel,
        generation_id=generation_id,
        state=state,
        error_type=type(error).__name__,
        retryable=bool(getattr(error, "retryable", False)),
    )


def _issue_for_channel(result: RetrievalChannelResult) -> RetrievalIssue | None:
    if result.state is RetrievalChannelState.corrupt:
        return RetrievalIssue(
            kind=RetrievalIssueKind.integrity,
            code=RetrievalIssueCode.corrupt_segment,
            channels=(result.channel,),
            error_type=result.error_type,
        )
    if result.state is RetrievalChannelState.unavailable:
        return RetrievalIssue(
            kind=RetrievalIssueKind.dependency,
            code=RetrievalIssueCode.provider_failure,
            channels=(result.channel,),
            retryable=result.retryable,
            error_type=result.error_type,
        )
    if result.state is RetrievalChannelState.refused:
        return RetrievalIssue(
            kind=RetrievalIssueKind.policy,
            code=RetrievalIssueCode.policy_refused,
            channels=(result.channel,),
            error_type=result.error_type,
        )
    return None


def _status_for_issues(issues: tuple[RetrievalIssue, ...]) -> RetrievalOutcomeStatus:
    kinds = {issue.kind for issue in issues}
    if RetrievalIssueKind.integrity in kinds:
        return RetrievalOutcomeStatus.integrity_error
    if RetrievalIssueKind.dependency in kinds:
        return RetrievalOutcomeStatus.dependency_error
    if RetrievalIssueKind.policy in kinds:
        return RetrievalOutcomeStatus.policy_refused
    return RetrievalOutcomeStatus.insufficient


def _build_outcome(
    *,
    mode: RetrievalMode,
    requested_generation_id: str,
    active_generation_id: str | None,
    channels: tuple[RetrievalChannelResult, ...],
    issues: tuple[RetrievalIssue, ...],
) -> RetrievalOutcome:
    status = _status_for_issues(issues) if issues else RetrievalOutcomeStatus.success
    body = {
        "active_generation_id": active_generation_id,
        "channels": [asdict(channel) for channel in channels],
        "issues": [asdict(issue) for issue in issues],
        "mode": mode.value,
        "requested_generation_id": requested_generation_id,
        "schema_version": "bijux.canon.retrieval.outcome.v1",
        "status": status.value,
    }
    return RetrievalOutcome(
        schema_version="bijux.canon.retrieval.outcome.v1",
        outcome_id=_outcome_id(body),
        mode=mode,
        requested_generation_id=requested_generation_id,
        active_generation_id=active_generation_id,
        status=status,
        channels=channels,
        issues=issues,
    )


class RetrievalOutcomeService:
    """Run required channels only against the verified active generation."""

    def __init__(
        self,
        registry_root: str | Path,
        *,
        compatibility: IndexCompatibility | None = None,
    ) -> None:
        self._registry = IndexGenerationRegistry(
            registry_root,
            compatibility=compatibility,
        )

    def execute(
        self,
        *,
        mode: RetrievalMode,
        generation_id: str,
        channel_runners: Mapping[RetrievalChannel, ChannelRunner],
    ) -> RetrievalOutcome:
        """Return success or typed non-usable state without partial fallback."""

        if not isinstance(mode, RetrievalMode):
            raise ValueError("retrieval outcome mode is unsupported")
        required = mode.required_channels
        unexpected = set(channel_runners).difference(required)
        if unexpected:
            raise ValueError("retrieval outcome received an unexpected channel runner")

        try:
            active_generation_id = self._registry.active_generation_id()
        except IndexActivationError as error:
            issue = RetrievalIssue(
                kind=RetrievalIssueKind.integrity,
                code=RetrievalIssueCode.corrupt_segment,
                channels=required,
                error_type=type(error).__name__,
            )
            return _build_outcome(
                mode=mode,
                requested_generation_id=generation_id,
                active_generation_id=None,
                channels=(),
                issues=(issue,),
            )
        if active_generation_id != generation_id:
            issue = RetrievalIssue(
                kind=RetrievalIssueKind.integrity,
                code=RetrievalIssueCode.stale_generation,
                channels=required,
            )
            return _build_outcome(
                mode=mode,
                requested_generation_id=generation_id,
                active_generation_id=active_generation_id,
                channels=(),
                issues=(issue,),
            )

        results = []
        issues = []
        for channel in required:
            runner = channel_runners.get(channel)
            if runner is None:
                issues.append(
                    RetrievalIssue(
                        kind=RetrievalIssueKind.insufficiency,
                        code=RetrievalIssueCode.missing_channel,
                        channels=(channel,),
                    )
                )
                continue
            try:
                result = runner()
            except Exception as error:
                result = _failed_channel(channel, generation_id, error)
            if result.channel is not channel:
                raise ValueError("retrieval runner returned the wrong channel")
            if result.generation_id != generation_id:
                issues.append(
                    RetrievalIssue(
                        kind=RetrievalIssueKind.integrity,
                        code=RetrievalIssueCode.stale_generation,
                        channels=(channel,),
                    )
                )
            channel_issue = _issue_for_channel(result)
            if channel_issue is not None:
                issues.append(channel_issue)
            results.append(result)

        if not issues:
            available_count = sum(
                result.state is RetrievalChannelState.available for result in results
            )
            empty_count = sum(
                result.state is RetrievalChannelState.empty for result in results
            )
            if empty_count == len(required):
                issues.append(
                    RetrievalIssue(
                        kind=RetrievalIssueKind.insufficiency,
                        code=RetrievalIssueCode.no_hits,
                        channels=required,
                    )
                )
            elif available_count and empty_count:
                issues.append(
                    RetrievalIssue(
                        kind=RetrievalIssueKind.insufficiency,
                        code=RetrievalIssueCode.sparse_results,
                        channels=tuple(
                            result.channel
                            for result in results
                            if result.state is RetrievalChannelState.empty
                        ),
                    )
                )

        return _build_outcome(
            mode=mode,
            requested_generation_id=generation_id,
            active_generation_id=active_generation_id,
            channels=tuple(results),
            issues=tuple(issues),
        )


def lexical_channel_result(batch: LexicalCandidateBatch) -> RetrievalChannelResult:
    """Return a sanitized channel result from lexical candidates."""

    if batch.outcome is LexicalCandidateOutcome.empty_query:
        raise ValueError("empty lexical queries must be rejected before retrieval")
    return RetrievalChannelResult.from_lexical(batch)


def dense_channel_result(
    batch: DenseCandidateBatch,
    *,
    required_mode: DenseCandidateMode,
) -> RetrievalChannelResult:
    """Return a sanitized channel result from the required dense backend."""

    if batch.mode is not required_mode:
        raise ValueError("dense retrieval result used the wrong backend mode")
    return RetrievalChannelResult.from_dense(batch)


__all__ = [
    "ChannelRunner",
    "RetrievalChannelResult",
    "RetrievalChannelState",
    "RetrievalEvidenceReference",
    "RetrievalIssue",
    "RetrievalIssueCode",
    "RetrievalIssueKind",
    "RetrievalMode",
    "RetrievalOutcome",
    "RetrievalOutcomeService",
    "RetrievalOutcomeStatus",
    "dense_channel_result",
    "lexical_channel_result",
]
