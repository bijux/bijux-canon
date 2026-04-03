# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import asdict, dataclass
from enum import Enum
from typing import Any, cast

from bijux_vex.core.contracts.determinism import DeterminismReport
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.types import Result


class ExecutionStatus(Enum):
    SUCCESS = "success"
    PARTIAL = "partial"
    FAILED = "failed"


@dataclass(frozen=True)
class ExecutionCost:
    vector_reads: int
    distance_computations: int
    graph_hops: int
    wall_time_estimate_ms: float
    cpu_time_ms: float = 0.0
    memory_estimate_mb: float = 0.0
    vector_ops: int = 0


@dataclass(frozen=True)
class WitnessReport:
    sample_k: int
    overlap_ratio: float
    rank_instability: float
    note: str = ""


@dataclass(frozen=True)
class ApproximationReport:
    recall_at_k: float
    rank_displacement: float
    distance_error: float
    algorithm: str = ""
    algorithm_version: str = ""
    backend: str = ""
    backend_version: str = ""
    randomness_sources: tuple[str, ...] = ()
    deterministic_fallback_used: bool = False
    truncation_ratio: float | None = None
    index_parameters: tuple[tuple[str, str | int | float], ...] = ()
    query_parameters: tuple[tuple[str, str | int | float], ...] = ()
    n_candidates: int = 0
    random_seed: int | None = None
    error_kind: str = "none"
    allowed_rank_jitter: int = 0
    allowed_recall_drop: float = 0.0
    rank_instability: float | None = None
    distance_margin: float | None = None
    similarity_entropy: float | None = None
    witness_report: WitnessReport | None = None
    calibrated_score_min: float | None = None
    calibrated_score_max: float | None = None
    calibration_note: str | None = None
    low_signal: bool = False
    adaptive_k_used: bool = False
    returned_k: int | None = None
    candidate_k: int | None = None
    index_hash: str | None = None
    stability_signature: str | None = None
    overlap_estimate: float | None = None
    confidence_label: str | None = None
    low_signal_threshold: float | None = None
    slo_met_latency: bool | None = None
    slo_met_recall: bool | None = None
    degraded: bool = False
    degradation_reason: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class ExecutionResult:
    execution_id: str
    signature: str
    artifact_id: str
    plan: ExecutionPlan
    results: tuple[Result, ...]
    cost: ExecutionCost
    approximation: ApproximationReport | None = None
    nd_result: NDResultSchema | None = None
    status: ExecutionStatus = ExecutionStatus.SUCCESS
    failure_reason: str | None = None
    randomness_sources: tuple[str, ...] = ()
    randomness_budget: tuple[tuple[str, int | float], ...] = ()
    randomness_envelopes: tuple[tuple[str, float], ...] = ()
    determinism_report: DeterminismReport | None = None

    def to_primitive(self) -> dict[str, Any]:
        def _flatten(obj: Any) -> Any:
            if isinstance(obj, Enum):
                return obj.value
            if isinstance(obj, dict):
                return {k: _flatten(v) for k, v in obj.items()}
            if hasattr(obj, "value"):
                return obj.value
            if isinstance(obj, tuple):
                return tuple(_flatten(o) for o in obj)
            if (
                hasattr(obj, "__dict__")
                or hasattr(obj, "__slots__")
                or hasattr(obj, "__dataclass_fields__")
            ):
                return {k: _flatten(v) for k, v in asdict(obj).items()}
            return obj

        return cast(dict[str, Any], _flatten(self))


__all__ = [
    "NDDecisionTrace",
    "NDResultSchema",
    "ExecutionResult",
    "ExecutionCost",
    "ApproximationReport",
    "ExecutionStatus",
    "WitnessReport",
]


@dataclass(frozen=True)
class NDDecisionTrace:
    runner: str
    params: tuple[tuple[str, object], ...]
    budget: tuple[tuple[str, object], ...]
    refusal: str | None = None
    degradation: str | None = None
    notes: tuple[str, ...] = ()


@dataclass(frozen=True)
class NDResultSchema:
    results: tuple[Result, ...]
    quality: ApproximationReport | None
    quality_reason: str | None
    confidence_label: str | None
    reproducibility_bounds: str
    refusal: str | None
    decision_trace: NDDecisionTrace | None
