# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Replay verified vector executions and compare persisted attempts."""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from enum import Enum
import math
from types import MappingProxyType
from typing import cast

from .artifacts import VexArtifactStore, VexExecutionArtifact, VexStoredArtifact


class VexReplayOutcome(str, Enum):
    """Stable comparison outcome for two persisted execution attempts."""

    exact_match = "exact_match"
    within_tolerance = "within_tolerance"
    diverged = "diverged"
    refused = "refused"


class VexDriftKind(str, Enum):
    """Immutable input drift that makes an attempt ineligible as a replay."""

    query_vector = "query_vector"
    generation = "generation"
    model = "model"
    filter = "filter"
    budget = "budget"
    backend = "backend"
    software = "software"
    hardware = "hardware"
    request = "request"
    plan = "plan"


@dataclass(frozen=True, slots=True)
class VexReplayInput:
    """Recursively immutable inputs recovered from a verified artifact."""

    request: Mapping[str, object]
    normalized_vector_sha256: str
    plan: Mapping[str, object]


@dataclass(frozen=True, slots=True)
class VexReplayComparison:
    """Typed comparison of an original attempt and its replay."""

    schema_version: str
    original_artifact_id: str
    replay_artifact_id: str
    original_execution_id: str
    replay_execution_id: str
    outcome: VexReplayOutcome
    drifts: tuple[VexDriftKind, ...]
    approximate_candidate_recall: float
    exact_candidate_recall: float
    maximum_score_delta: float | None


VexReplayExecutor = Callable[[VexReplayInput], VexExecutionArtifact]


def _freeze(value: object) -> object:
    if isinstance(value, Mapping):
        return MappingProxyType(
            {str(key): _freeze(item) for key, item in value.items()}
        )
    if isinstance(value, list | tuple):
        return tuple(_freeze(item) for item in value)
    return value


def _mapping(record: Mapping[str, object], key: str) -> Mapping[str, object]:
    value = record.get(key)
    if not isinstance(value, Mapping):
        raise ValueError(f"VEX artifact {key} must be a JSON object")
    return cast(Mapping[str, object], value)


def _sequence(record: Mapping[str, object], key: str) -> Sequence[object]:
    value = record.get(key)
    if not isinstance(value, list | tuple):
        raise ValueError(f"VEX artifact {key} must be a JSON array")
    return value


def _changed_keys(
    original: Mapping[str, object], replay: Mapping[str, object]
) -> set[str]:
    return {
        key
        for key in original.keys() | replay.keys()
        if original.get(key) != replay.get(key)
    }


def _identity_drifts(
    original: Mapping[str, object], replay: Mapping[str, object]
) -> tuple[VexDriftKind, ...]:
    drifts: list[VexDriftKind] = []

    def add(kind: VexDriftKind) -> None:
        if kind not in drifts:
            drifts.append(kind)

    if original.get("normalized_vector_sha256") != replay.get(
        "normalized_vector_sha256"
    ):
        add(VexDriftKind.query_vector)

    original_request = _mapping(original, "request")
    replay_request = _mapping(replay, "request")
    request_keys = _changed_keys(original_request, replay_request)
    request_groups = (
        (VexDriftKind.generation, {"generation", "generation_id"}),
        (
            VexDriftKind.model,
            {"model", "model_id", "model_lock", "model_lock_artifact_id"},
        ),
        (VexDriftKind.filter, {"filter", "filters", "filter_sha256"}),
        (VexDriftKind.budget, {"budget", "budgets"}),
    )
    for kind, keys in request_groups:
        if request_keys & keys:
            add(kind)
            request_keys -= keys
    if request_keys:
        add(VexDriftKind.request)

    original_plan = _mapping(original, "plan")
    replay_plan = _mapping(replay, "plan")
    plan_keys = _changed_keys(original_plan, replay_plan)
    plan_groups = (
        (
            VexDriftKind.backend,
            {"backend", "backend_version", "algorithm", "algorithm_version"},
        ),
        (VexDriftKind.software, {"software", "software_locks"}),
        (VexDriftKind.hardware, {"hardware", "hardware_class"}),
    )
    for kind, keys in plan_groups:
        if plan_keys & keys:
            add(kind)
            plan_keys -= keys
    if plan_keys:
        add(VexDriftKind.plan)

    original_witness = _mapping(original, "witness")
    replay_witness = _mapping(replay, "witness")
    witness_groups = (
        (VexDriftKind.generation, {"generation_id"}),
        (VexDriftKind.model, {"model_lock_artifact_id"}),
        (VexDriftKind.query_vector, {"query_vector_sha256"}),
        (VexDriftKind.filter, {"filter_sha256"}),
        (VexDriftKind.backend, {"backend", "backend_version"}),
        (
            VexDriftKind.plan,
            {"metric", "normalization", "schema_version", "top_k"},
        ),
    )
    witness_keys = _changed_keys(original_witness, replay_witness)
    witness_keys -= {
        "candidate_order_sha256",
        "candidates",
        "result_sha256",
        "witness_id",
    }
    for kind, keys in witness_groups:
        if witness_keys & keys:
            add(kind)
            witness_keys -= keys
    if witness_keys:
        add(VexDriftKind.plan)
    return tuple(drifts)


def _ranked_candidates(
    value: Sequence[object], *, label: str
) -> tuple[tuple[str, str, int, float], ...]:
    candidates: list[tuple[str, str, int, float]] = []
    for item in value:
        if not isinstance(item, Mapping):
            raise ValueError(f"VEX {label} candidates must be JSON objects")
        chunk_id = item.get("chunk_id")
        source = item.get("source", label)
        rank = item.get("rank")
        score = item.get("score")
        if (
            not isinstance(chunk_id, str)
            or not isinstance(source, str)
            or not isinstance(rank, int)
            or isinstance(score, bool)
            or not isinstance(score, int | float)
            or not math.isfinite(float(score))
        ):
            raise ValueError(f"VEX {label} candidate is invalid")
        candidates.append((source, chunk_id, rank, float(score)))
    return tuple(candidates)


def _candidate_recall(
    original: tuple[tuple[str, str, int, float], ...],
    replay: tuple[tuple[str, str, int, float], ...],
) -> float:
    if not original:
        return 1.0 if not replay else 0.0
    expected = {(source, chunk_id) for source, chunk_id, _, _ in original}
    actual = {(source, chunk_id) for source, chunk_id, _, _ in replay}
    return len(expected & actual) / len(expected)


def _maximum_score_delta(
    pairs: Sequence[
        tuple[
            tuple[str, str, int, float],
            tuple[str, str, int, float],
        ]
    ],
) -> float | None:
    if not pairs:
        return None
    return max(abs(original[3] - replay[3]) for original, replay in pairs)


def compare_vex_artifacts(
    original: VexStoredArtifact,
    replay: VexStoredArtifact,
    *,
    score_tolerance: float = 1e-6,
) -> VexReplayComparison:
    """Compare two verified stored attempts without ignoring identity drift."""

    if not math.isfinite(score_tolerance) or score_tolerance < 0:
        raise ValueError("VEX replay score tolerance must be finite and non-negative")
    drifts = _identity_drifts(original.record, replay.record)

    original_approximate = _ranked_candidates(
        _sequence(original.record, "candidate_order"), label="approximate"
    )
    replay_approximate = _ranked_candidates(
        _sequence(replay.record, "candidate_order"), label="approximate"
    )
    original_exact = _ranked_candidates(
        _sequence(_mapping(original.record, "witness"), "candidates"),
        label="exact",
    )
    replay_exact = _ranked_candidates(
        _sequence(_mapping(replay.record, "witness"), "candidates"),
        label="exact",
    )
    pairs = tuple(zip(original_approximate, replay_approximate, strict=False)) + tuple(
        zip(original_exact, replay_exact, strict=False)
    )
    maximum_delta = _maximum_score_delta(pairs)
    same_candidate_shape = (
        len(original_approximate) == len(replay_approximate)
        and len(original_exact) == len(replay_exact)
        and all(left[:3] == right[:3] for left, right in pairs)
    )
    exact_outputs = same_candidate_shape and all(
        left[3] == right[3] for left, right in pairs
    )
    within_tolerance = (
        same_candidate_shape
        and maximum_delta is not None
        and maximum_delta <= score_tolerance
    )
    if drifts:
        outcome = VexReplayOutcome.refused
    elif exact_outputs:
        outcome = VexReplayOutcome.exact_match
    elif within_tolerance:
        outcome = VexReplayOutcome.within_tolerance
    else:
        outcome = VexReplayOutcome.diverged

    return VexReplayComparison(
        schema_version="bijux.canon.vex.replay_comparison.v1",
        original_artifact_id=original.artifact_id,
        replay_artifact_id=replay.artifact_id,
        original_execution_id=str(original.record.get("execution_id", "")),
        replay_execution_id=str(replay.record.get("execution_id", "")),
        outcome=outcome,
        drifts=drifts,
        approximate_candidate_recall=_candidate_recall(
            original_approximate, replay_approximate
        ),
        exact_candidate_recall=_candidate_recall(original_exact, replay_exact),
        maximum_score_delta=maximum_delta,
    )


def replay_vex_execution(
    store: VexArtifactStore,
    original_artifact_id: str,
    executor: VexReplayExecutor,
    *,
    score_tolerance: float = 1e-6,
) -> VexReplayComparison:
    """Re-execute verified immutable inputs, persist the attempt, and compare it."""

    original = store.load(original_artifact_id)
    replay_input = VexReplayInput(
        request=cast(
            Mapping[str, object], _freeze(_mapping(original.record, "request"))
        ),
        normalized_vector_sha256=str(original.record["normalized_vector_sha256"]),
        plan=cast(Mapping[str, object], _freeze(_mapping(original.record, "plan"))),
    )
    replay = store.put(executor(replay_input))
    return compare_vex_artifacts(
        original,
        replay,
        score_tolerance=score_tolerance,
    )


__all__ = [
    "VexDriftKind",
    "VexReplayComparison",
    "VexReplayExecutor",
    "VexReplayInput",
    "VexReplayOutcome",
    "compare_vex_artifacts",
    "replay_vex_execution",
]
