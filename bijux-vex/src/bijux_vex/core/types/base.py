# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi

from __future__ import annotations

from dataclasses import dataclass, field, fields
from typing import TYPE_CHECKING as _TYPE_CHECKING

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.execution_intent import ExecutionIntent
from bijux_vex.core.execution_mode import ExecutionMode

if _TYPE_CHECKING:  # pragma: no cover
    from bijux_vex.core.contracts.determinism import DeterminismReport
    from bijux_vex.core.execution_result import ApproximationReport
    from bijux_vex.core.runtime.execution_plan import ExecutionPlan


@dataclass(frozen=True)
class Document:
    document_id: str
    text: str
    source: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class Chunk:
    chunk_id: str
    document_id: str
    text: str
    ordinal: int
    start_offset: int | None = None
    end_offset: int | None = None


@dataclass(frozen=True)
class Vector:
    vector_id: str
    chunk_id: str
    values: tuple[float, ...]
    dimension: int
    model: str | None = None
    metadata: tuple[tuple[str, str], ...] | dict[str, str] | None = None

    def __post_init__(self) -> None:
        if self.dimension <= 0:
            raise InvariantError(message="vector dimension must be positive")
        object.__setattr__(self, "values", tuple(self.values))
        if self.metadata is not None:
            if isinstance(self.metadata, dict):
                metadata = tuple((str(k), str(v)) for k, v in self.metadata.items())
            else:
                metadata = tuple((str(k), str(v)) for k, v in self.metadata)
            object.__setattr__(self, "metadata", metadata)
        if len(self.values) != self.dimension:
            raise InvariantError(
                message="vector values length must match declared dimension"
            )


@dataclass(frozen=True)
class ModelSpec:
    model_id: str
    dimension: int
    vendor: str | None = None
    version: str | None = None


@dataclass(frozen=True)
class ExecutionBudget:
    max_latency_ms: int | None = None
    max_memory_mb: int | None = None
    max_error: float | None = None
    max_vectors: int | None = None
    max_distance_computations: int | None = None
    max_ann_probes: int | None = None


@dataclass(frozen=True)
class NDSettings:
    profile: str | None = None
    target_recall: float | None = None
    latency_budget_ms: int | None = None
    witness_rate: float | None = None
    witness_sample_k: int | None = None
    witness_mode: str | None = None
    build_on_demand: bool = False
    candidate_k: int | None = None
    diversity_lambda: float | None = None
    normalize_vectors: bool = False
    normalize_query: bool = False
    outlier_threshold: float | None = None
    low_signal_margin: float | None = None
    adaptive_k: bool = False
    low_signal_refuse: bool = False
    replay_strict: bool = False
    warmup_queries: str | None = None
    incremental_index: bool | None = None
    max_candidates: int | None = None
    max_index_memory_mb: int | None = None
    two_stage: bool = True
    m: int | None = None
    ef_construction: int | None = None
    ef_search: int | None = None
    max_ef_search: int | None = None
    space: str | None = None


@dataclass(frozen=True)
class ExecutionRequest:
    request_id: str
    text: str | None
    vector: tuple[float, ...] | None
    top_k: int
    execution_contract: ExecutionContract
    execution_intent: ExecutionIntent
    execution_mode: ExecutionMode = ExecutionMode.STRICT
    execution_budget: ExecutionBudget | None = None
    nd_settings: NDSettings | None = None
    model: ModelSpec | None = None

    def __post_init__(self) -> None:
        if not isinstance(self.execution_contract, ExecutionContract):
            raise InvariantError(
                message="execution_contract is required for ExecutionRequest construction"
            )
        if not isinstance(self.execution_intent, ExecutionIntent):
            raise InvariantError(
                message="execution_intent must be a known ExecutionIntent"
            )
        if not isinstance(self.execution_mode, ExecutionMode):
            raise InvariantError(
                message="execution_mode must be one of strict|bounded|exploratory"
            )

        if self.execution_contract is ExecutionContract.DETERMINISTIC:
            if self.execution_mode is not ExecutionMode.STRICT:
                raise InvariantError(
                    message="deterministic executions must use strict mode"
                )
            if self.nd_settings is not None:
                raise InvariantError(
                    message="nd_settings not allowed for deterministic execution"
                )
        else:
            if self.execution_mode is ExecutionMode.STRICT:
                raise InvariantError(
                    message="non_deterministic executions require bounded or exploratory mode"
                )
            if self.execution_budget is None:
                raise InvariantError(
                    message="execution_budget required for non_deterministic execution"
                )
            if self.nd_settings is not None:
                if self.nd_settings.profile not in {
                    None,
                    "fast",
                    "balanced",
                    "accurate",
                }:
                    raise InvariantError(
                        message="nd_settings.profile must be fast|balanced|accurate"
                    )
                if self.nd_settings.target_recall is not None and not (
                    0.0 < self.nd_settings.target_recall <= 1.0
                ):
                    raise InvariantError(
                        message="nd_settings.target_recall must be within (0,1]"
                    )
                if (
                    self.nd_settings.low_signal_margin is not None
                    and self.nd_settings.low_signal_margin <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.low_signal_margin must be positive"
                    )
                if (
                    self.nd_settings.diversity_lambda is not None
                    and not 0.0 <= self.nd_settings.diversity_lambda <= 1.0
                ):
                    raise InvariantError(
                        message="nd_settings.diversity_lambda must be within [0,1]"
                    )
                if (
                    self.nd_settings.candidate_k is not None
                    and self.nd_settings.candidate_k < self.top_k
                ):
                    raise InvariantError(
                        message="nd_settings.candidate_k must be >= top_k"
                    )
                if (
                    self.nd_settings.latency_budget_ms is not None
                    and self.nd_settings.latency_budget_ms <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.latency_budget_ms must be positive"
                    )
                if self.nd_settings.witness_rate is not None and not (
                    0.0 < self.nd_settings.witness_rate <= 1.0
                ):
                    raise InvariantError(
                        message="nd_settings.witness_rate must be within (0,1]"
                    )
                if self.nd_settings.witness_mode not in {
                    None,
                    "off",
                    "sample",
                    "full",
                }:
                    raise InvariantError(
                        message="nd_settings.witness_mode must be off|sample|full"
                    )
                if (
                    self.nd_settings.witness_sample_k is not None
                    and self.nd_settings.witness_sample_k <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.witness_sample_k must be positive"
                    )
                if (
                    self.nd_settings.max_index_memory_mb is not None
                    and self.nd_settings.max_index_memory_mb <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.max_index_memory_mb must be positive"
                    )
                if self.nd_settings.m is not None and self.nd_settings.m <= 0:
                    raise InvariantError(message="nd_settings.m must be positive")
                if (
                    self.nd_settings.ef_construction is not None
                    and self.nd_settings.ef_construction <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.ef_construction must be positive"
                    )
                if (
                    self.nd_settings.ef_search is not None
                    and self.nd_settings.ef_search <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.ef_search must be positive"
                    )
                if (
                    self.nd_settings.max_ef_search is not None
                    and self.nd_settings.max_ef_search <= 0
                ):
                    raise InvariantError(
                        message="nd_settings.max_ef_search must be positive"
                    )
                if self.nd_settings.space not in {None, "l2", "cosine", "ip"}:
                    raise InvariantError(
                        message="nd_settings.space must be l2|cosine|ip"
                    )
        if self.vector is not None:
            object.__setattr__(self, "vector", tuple(self.vector))


@dataclass(frozen=True)
class Result:
    request_id: str
    document_id: str
    chunk_id: str
    vector_id: str
    artifact_id: str
    score: float
    rank: int


@dataclass(frozen=True)
class ExecutionArtifact:
    artifact_id: str
    corpus_fingerprint: str
    vector_fingerprint: str
    metric: str
    scoring_version: str
    execution_contract: ExecutionContract
    execution_artifact_version: str = "1.0"
    schema_version: str = "v1"
    cold_start_ready: bool = True
    warm_cache_hint: bool = False
    build_params: tuple[tuple[str, str], ...] = field(default_factory=tuple)
    index_config_fingerprint: str | None = None
    index_state: str = "ready"
    artifact_fingerprint: str | None = None
    execution_id: str | None = None
    execution_plan: ExecutionPlan | None = None
    execution_signature: str | None = None
    approximation_report: ApproximationReport | None = None
    determinism_report: DeterminismReport | None = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self, "build_params", tuple(tuple(p) for p in self.build_params)
        )
        allowed = {f.name for f in fields(self)}
        unknown = set(self.__dict__) - allowed
        if unknown:
            raise InvariantError(
                message=f"Unknown fields for ExecutionArtifact: {sorted(unknown)}"
            )
        if self.schema_version not in {"v1"}:
            raise InvariantError(
                message=f"Unsupported ExecutionArtifact schema_version: {self.schema_version}"
            )
        if self.execution_artifact_version not in {"1.0"}:
            raise InvariantError(
                message=f"Unsupported execution_artifact_version: {self.execution_artifact_version}"
            )
        plan = self.execution_plan
        if not self.execution_id:
            from bijux_vex.core.runtime.vector_execution import derive_execution_id

            placeholder_request = ExecutionRequest(
                request_id=f"{self.artifact_id}-execution",
                text=None,
                vector=None,
                top_k=0,
                execution_contract=self.execution_contract,
                execution_intent=ExecutionIntent.EXACT_VALIDATION,
                execution_mode=ExecutionMode.STRICT
                if self.execution_contract is ExecutionContract.DETERMINISTIC
                else ExecutionMode.BOUNDED,
                execution_budget=ExecutionBudget(
                    max_latency_ms=0, max_memory_mb=0, max_error=0.0
                )
                if self.execution_contract is ExecutionContract.NON_DETERMINISTIC
                else None,
            )
            object.__setattr__(
                self,
                "execution_id",
                derive_execution_id(
                    request=placeholder_request,
                    backend_id="unknown",
                    algorithm="exact_vector_execution",
                    plan=plan,
                ),
            )
        if plan and not self.execution_signature:
            from bijux_vex.core.runtime.vector_execution import execution_signature

            object.__setattr__(
                self,
                "execution_signature",
                execution_signature(
                    plan=plan,
                    corpus_fingerprint=self.corpus_fingerprint,
                    vector_fingerprint=self.vector_fingerprint,
                    randomness=None,
                ),
            )
        if not self.index_config_fingerprint:
            from bijux_vex.core.identity.ids import fingerprint

            object.__setattr__(
                self,
                "index_config_fingerprint",
                fingerprint(tuple(sorted(self.build_params))),
            )
        from bijux_vex.core.invariants import validate_execution_artifact

        validate_execution_artifact(self)

    @property
    def replayable(self) -> bool:
        """Derived property: deterministic artifacts are replayable."""
        return self.execution_contract is ExecutionContract.DETERMINISTIC
