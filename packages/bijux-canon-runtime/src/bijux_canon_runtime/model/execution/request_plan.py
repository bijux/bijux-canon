# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed v2 request inputs and their concrete Runtime DAG plan."""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
import math
from pathlib import Path
import re

from bijux_canon_runtime.ontology.ids import ArtifactID, RequestID
from bijux_canon_runtime.ontology.public import ReplayMode

SUPPORTED_LOCAL_REASON_PROVIDERS = ("credential-free", "local-recorded")
MAX_RUNTIME_TIMEOUT_SECONDS = 604_800.0


class RuntimeRequestOperation(StrEnum):
    """User operations that expand into one or more typed DAG nodes."""

    CORPUS_PREPARE = "corpus.prepare"
    INDEX_BUILD = "index.build"
    RETRIEVE = "retrieve"
    ASK = "ask"
    RESEARCH = "research"
    RUN = "run"
    REPLAY = "replay"


class DagOperation(StrEnum):
    """Exclusive single-operation node kinds in a Runtime DAG."""

    INGEST = "ingest"
    SNAPSHOT = "snapshot"
    EMBED = "embed"
    LEXICAL_INDEX = "lexical-index"
    DENSE_INDEX = "dense-index"
    RETRIEVE = "retrieve"
    REASON = "reason"
    AGENT = "agent"
    VERIFY = "verify"
    PERSIST = "persist"
    PUBLISH = "publish"


class ExecutionProfile(StrEnum):
    """Supported local and service-backed execution profiles."""

    OFFLINE_LEXICAL = "offline-lexical"
    LOCAL_HYBRID_EXACT = "local-hybrid-exact"
    LOCAL_HYBRID_ANN = "local-hybrid-ann"
    QDRANT_HYBRID = "qdrant-hybrid"


@dataclass(frozen=True, slots=True)
class RuntimeRequestBudget:
    """Hard bounds copied into every concrete step that consumes them."""

    timeout_seconds: float
    max_artifact_bytes: int
    max_steps: int | None = None
    max_provider_tokens: int | None = None

    def __post_init__(self) -> None:
        if (
            not math.isfinite(self.timeout_seconds)
            or self.timeout_seconds <= 0
            or self.timeout_seconds > MAX_RUNTIME_TIMEOUT_SECONDS
        ):
            raise ValueError(
                "runtime timeout must be finite, positive, and no greater than "
                f"{MAX_RUNTIME_TIMEOUT_SECONDS:g} seconds"
            )
        if self.max_artifact_bytes < 1:
            raise ValueError("runtime artifact budget must be positive")
        if self.max_steps is not None and self.max_steps < 1:
            raise ValueError("runtime step budget must be positive")
        if self.max_provider_tokens is not None and self.max_provider_tokens < 1:
            raise ValueError("provider token budget must be positive")


@dataclass(frozen=True, slots=True)
class RetrievalFilters:
    """Exact immutable filters for request planning and replay."""

    document_ids: tuple[str, ...] = ()
    source_uris: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if any(not value.strip() for value in (*self.document_ids, *self.source_uris)):
            raise ValueError("retrieval filters must not contain empty values")
        if len(set(self.document_ids)) != len(self.document_ids):
            raise ValueError("retrieval document filters must be unique")
        if len(set(self.source_uris)) != len(self.source_uris):
            raise ValueError("retrieval source filters must be unique")
        if len(self.document_ids) > 1000 or len(self.source_uris) > 1000:
            raise ValueError("retrieval filter collections must not exceed 1000 items")


@dataclass(frozen=True, slots=True)
class RuntimeOutputPolicy:
    """Answer and publication requirements copied into reasoning descendants."""

    require_citations: bool
    permit_insufficient_answer: bool
    publish: bool


@dataclass(frozen=True, slots=True)
class RuntimeOperationRequest:
    """Normalized user request before deterministic DAG expansion."""

    request_id: RequestID
    operation: RuntimeRequestOperation
    execution_profile: ExecutionProfile
    budget: RuntimeRequestBudget
    replay_mode: ReplayMode
    scope: str
    query: str | None = None
    source_directory: str | None = None
    corpus_id: ArtifactID | None = None
    index_id: ArtifactID | None = None
    filters: RetrievalFilters = field(default_factory=RetrievalFilters)
    top_k: int | None = None
    provider: str | None = None
    output_policy: RuntimeOutputPolicy | None = None
    replay_attempt_id: str | None = None
    execution_configuration_sha256: str | None = None
    source_selection_artifact_id: ArtifactID | None = None
    parent_job_id: str | None = None

    def __post_init__(self) -> None:
        if not str(self.request_id).strip() or not self.scope.strip():
            raise ValueError("request identity and scope must not be empty")
        if self.query is not None and not self.query.strip():
            raise ValueError("request query must not be empty")
        if self.source_directory is not None:
            directory = Path(self.source_directory)
            if not directory.is_absolute():
                raise ValueError("source directory must be an absolute local path")
        if self.top_k is not None and not 1 <= self.top_k <= 1000:
            raise ValueError("retrieval top_k must be between 1 and 1000")
        if self.provider is not None and not self.provider.strip():
            raise ValueError("provider identity must not be empty")
        if (
            self.execution_configuration_sha256 is not None
            and re.fullmatch(r"[0-9a-f]{64}", self.execution_configuration_sha256)
            is None
        ):
            raise ValueError("execution configuration identity must be a sha256")
        if self.parent_job_id is not None and not self.parent_job_id.strip():
            raise ValueError("parent job identity must not be empty")
        self._validate_operation_inputs()

    def _validate_operation_inputs(self) -> None:
        if self.operation is RuntimeRequestOperation.CORPUS_PREPARE:
            if self.source_directory is None:
                raise ValueError("corpus.prepare requires a source directory")
            return
        if self.operation is RuntimeRequestOperation.INDEX_BUILD:
            if self.corpus_id is None:
                raise ValueError("index.build requires a corpus artifact")
            return
        if self.operation is RuntimeRequestOperation.RETRIEVE:
            if self.query is None or self.index_id is None or self.top_k is None:
                raise ValueError("retrieve requires query, index artifact, and top_k")
            return
        if self.operation in {
            RuntimeRequestOperation.ASK,
            RuntimeRequestOperation.RESEARCH,
        }:
            if (
                self.query is None
                or self.index_id is None
                or self.top_k is None
                or self.provider is None
                or self.output_policy is None
            ):
                raise ValueError(
                    f"{self.operation.value} requires retrieval and output inputs"
                )
            return
        if self.operation in {
            RuntimeRequestOperation.RUN,
            RuntimeRequestOperation.REPLAY,
        }:
            if (
                self.query is None
                or self.top_k is None
                or (self.source_directory is None and self.corpus_id is None)
            ):
                raise ValueError(
                    f"{self.operation.value} requires retrieval and corpus inputs"
                )
            if self.source_directory is not None and self.corpus_id is not None:
                raise ValueError(
                    f"{self.operation.value} accepts directory or corpus, not both"
                )
            if self.provider is None or self.output_policy is None:
                raise ValueError(
                    f"{self.operation.value} requires provider and output policy"
                )
            if self.operation is RuntimeRequestOperation.REPLAY and not (
                self.replay_attempt_id and self.replay_attempt_id.strip()
            ):
                raise ValueError("replay requires an immutable source attempt")


@dataclass(frozen=True, slots=True)
class ConcreteStepInputs:
    """Typed request fields consumed by one specific DAG operation."""

    request_id: RequestID
    request_operation: RuntimeRequestOperation
    execution_profile: ExecutionProfile
    budget: RuntimeRequestBudget
    replay_mode: ReplayMode
    scope: str
    query: str | None = None
    source_directory: str | None = None
    corpus_id: ArtifactID | None = None
    index_id: ArtifactID | None = None
    filters: RetrievalFilters | None = None
    top_k: int | None = None
    provider: str | None = None
    output_policy: RuntimeOutputPolicy | None = None
    replay_attempt_id: str | None = None
    source_attempt_id: str | None = None
    execution_configuration_sha256: str | None = None
    source_selection_artifact_id: ArtifactID | None = None
    parent_job_id: str | None = None


@dataclass(frozen=True, slots=True)
class ConcreteDagStep:
    """One executable operation with explicit edges and artifact contracts."""

    step_id: str
    operation: DagOperation
    depends_on: tuple[str, ...]
    input_artifact_contract_ids: tuple[str, ...]
    output_artifact_contract_ids: tuple[str, ...]
    inputs: ConcreteStepInputs


@dataclass(frozen=True, slots=True)
class RuntimeRequestPlan:
    """Deterministic typed DAG produced from one normalized real request."""

    schema_version: str
    request_id: RequestID
    request_operation: RuntimeRequestOperation
    request_sha256: str
    plan_sha256: str
    entry_step_ids: tuple[str, ...]
    terminal_step_ids: tuple[str, ...]
    steps: tuple[ConcreteDagStep, ...]


__all__ = [
    "ConcreteDagStep",
    "ConcreteStepInputs",
    "DagOperation",
    "ExecutionProfile",
    "MAX_RUNTIME_TIMEOUT_SECONDS",
    "RetrievalFilters",
    "RuntimeOperationRequest",
    "RuntimeOutputPolicy",
    "RuntimeRequestBudget",
    "RuntimeRequestOperation",
    "RuntimeRequestPlan",
    "SUPPORTED_LOCAL_REASON_PROVIDERS",
]
