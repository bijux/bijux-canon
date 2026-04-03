# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
import math
import random

from bijux_vex.core.execution_result import WitnessReport
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.types import Result
from bijux_vex.domain.execution_requests.compare import _rank_instability
from bijux_vex.domain.execution_requests.scoring import tie_break_key


@dataclass(frozen=True)
class NDQualityMetrics:
    rank_instability: float
    distance_margin: float
    similarity_entropy: float


def _sorted_results(results: Iterable[Result]) -> list[Result]:
    ordered = list(results)
    if all(res.rank for res in ordered):
        ordered.sort(key=lambda res: res.rank)
    else:
        ordered.sort(key=tie_break_key)
    return ordered


def compute_distance_margin(results: Iterable[Result]) -> float:
    ordered = _sorted_results(results)
    if len(ordered) < 2:
        return 0.0
    margins = [
        abs(ordered[idx + 1].score - ordered[idx].score)
        for idx in range(len(ordered) - 1)
    ]
    return float(sum(margins) / len(margins)) if margins else 0.0


def compute_similarity_entropy(results: Iterable[Result]) -> float:
    ordered = _sorted_results(results)
    if len(ordered) <= 1:
        return 0.0
    scores = [res.score for res in ordered]
    max_score = max(scores)
    weights = [(max_score - score) + 1e-9 for score in scores]
    total = sum(weights)
    if total <= 0:
        return 0.0
    probs = [w / total for w in weights]
    entropy = -sum(p * math.log(p) for p in probs if p > 0)
    return float(entropy / math.log(len(probs)))


def compute_rank_instability(
    results: Iterable[Result], exact_results: Iterable[Result] | None
) -> float:
    ordered = _sorted_results(results)
    if exact_results is None:
        return 0.0
    exact_ordered = _sorted_results(exact_results)
    ids_a = [res.vector_id for res in ordered]
    ids_b = [res.vector_id for res in exact_ordered]
    overlap = set(ids_a) & set(ids_b)
    return _rank_instability(ids_a, ids_b, overlap)


def build_witness_report(
    nd_results: Iterable[Result],
    exact_results: Iterable[Result],
    sample_k: int,
) -> WitnessReport:
    ordered_nd = _sorted_results(nd_results)
    ordered_exact = _sorted_results(exact_results)
    ids_nd = [res.vector_id for res in ordered_nd]
    ids_exact = [res.vector_id for res in ordered_exact]
    overlap = set(ids_nd) & set(ids_exact)
    overlap_ratio = len(overlap) / float(len(ids_exact) or 1)
    rank_instability = _rank_instability(ids_nd, ids_exact, overlap)
    note = f"witness overlap {overlap_ratio:.2f} on top {sample_k}"
    return WitnessReport(
        sample_k=sample_k,
        overlap_ratio=overlap_ratio,
        rank_instability=rank_instability,
        note=note,
    )


def should_run_witness(rate: float, seed: int | None) -> bool:
    if rate <= 0:
        return False
    if rate >= 1:
        return True
    rng = random.Random(seed)  # noqa: S311  # nosec B311 - deterministic witness sampling
    return rng.random() < rate


def similarity_from_score(metric: str, score: float) -> float:
    if metric in {"l2", "cosine"}:
        return -score
    if metric == "dot":
        return score
    return -score


def adaptive_filter_results(
    metric: str,
    results: list[Result],
    threshold: float | None,
    adaptive_k: bool,
) -> tuple[list[Result], bool, bool]:
    if threshold is None:
        return results, False, False
    filtered: list[Result] = []
    for res in results:
        sim = similarity_from_score(metric, res.score)
        if sim >= threshold or not adaptive_k:
            filtered.append(res)
    degraded = len(filtered) < len(results)
    low_signal = adaptive_k and not filtered
    return filtered, degraded, low_signal


def calibrate_scores(
    metric: str, results: Iterable[Result]
) -> tuple[float | None, float | None, str | None]:
    ordered = _sorted_results(results)
    if not ordered:
        return None, None, None
    sims = [similarity_from_score(metric, res.score) for res in ordered]
    min_sim = min(sims)
    max_sim = max(sims)
    note = (
        "similarity derived from metric; cross-backend comparisons require identical "
        "metric + normalization"
    )
    return min_sim, max_sim, note


def stability_signature(metric: str, results: Iterable[Result]) -> str:
    ordered = _sorted_results(results)
    payload = {
        "metric": metric,
        "ids": tuple(res.vector_id for res in ordered),
        "margin": round(compute_distance_margin(ordered), 6),
        "entropy": round(compute_similarity_entropy(ordered), 6),
    }
    return fingerprint(payload)


__all__ = [
    "NDQualityMetrics",
    "compute_distance_margin",
    "compute_similarity_entropy",
    "compute_rank_instability",
    "build_witness_report",
    "should_run_witness",
    "similarity_from_score",
    "adaptive_filter_results",
    "calibrate_scores",
    "stability_signature",
]
