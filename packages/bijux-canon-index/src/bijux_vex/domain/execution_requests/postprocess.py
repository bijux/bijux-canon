# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import replace

from bijux_vex.core.contracts.determinism import DeterminismReport
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.execution_result import (
    ApproximationReport,
    ExecutionCost,
    ExecutionResult,
    ExecutionStatus,
    NDDecisionTrace,
    NDResultSchema,
    WitnessReport,
)
from bijux_vex.core.runtime.execution_session import ExecutionSession
from bijux_vex.core.runtime.vector_execution import execution_signature
from bijux_vex.core.types import Result
from bijux_vex.domain.execution_requests.budget import apply_budget_outcomes
from bijux_vex.domain.execution_requests.nd_quality import (
    calibrate_scores,
    compute_distance_margin,
    compute_rank_instability,
    compute_similarity_entropy,
    stability_signature,
)
from bijux_vex.domain.nd.randomness import enforce_randomness_contract


def randomness_audit(
    session: ExecutionSession,
) -> tuple[
    tuple[str, ...], tuple[tuple[str, int | float], ...], tuple[tuple[str, float], ...]
]:
    randomness_sources: tuple[str, ...] = ()
    randomness_budget: tuple[tuple[str, int | float], ...] = ()
    randomness_envelopes: tuple[tuple[str, float], ...] = ()
    if session.randomness:
        randomness_sources = tuple(session.randomness.sources)
        randomness_budget = tuple(sorted((session.randomness.budget or {}).items()))
        randomness_envelopes = tuple(session.randomness.envelopes)
    return randomness_sources, randomness_budget, randomness_envelopes


def guard_nd_randomness(
    session: ExecutionSession,
    randomness_sources: tuple[str, ...],
    randomness_budget: tuple[tuple[str, int | float], ...],
    randomness_envelopes: tuple[tuple[str, float], ...],
    approximation: ApproximationReport | None,
) -> None:
    if session.request.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
        return
    if (
        not randomness_sources
        or randomness_budget is None
        or randomness_envelopes is None
    ):
        raise InvariantError(
            message="Non-deterministic execution missing randomness audit data"
        )
    enforce_randomness_contract(session, approximation is not None)


def apply_budget_results(
    session: ExecutionSession,
    approximation: ApproximationReport | None,
    cost: ExecutionCost,
    status: ExecutionStatus,
    failure_reason: str | None,
) -> tuple[ExecutionStatus, str | None]:
    return apply_budget_outcomes(
        session.request,
        approximation,
        cost,
        status,
        failure_reason,
    )


def build_execution_result(
    session: ExecutionSession,
    results_buffer: tuple[Result, ...] | list[Result],
    approximation: ApproximationReport | None,
    cost: ExecutionCost,
    status: ExecutionStatus,
    failure_reason: str | None,
    randomness_sources: tuple[str, ...],
    randomness_budget: tuple[tuple[str, int | float], ...],
    randomness_envelopes: tuple[tuple[str, float], ...],
    witness_report: WitnessReport | None = None,
    witness_results: tuple[Result, ...] | None = None,
    decision_trace: NDDecisionTrace | None = None,
) -> ExecutionResult:
    signature = execution_signature(
        plan=session.plan,
        corpus_fingerprint=session.artifact.corpus_fingerprint,
        vector_fingerprint=session.artifact.vector_fingerprint,
        randomness=session.randomness,
    )
    determinism_report = None
    if session.request.execution_contract is ExecutionContract.NON_DETERMINISTIC:
        determinism_report = DeterminismReport(
            randomness_sources=randomness_sources,
            reproducibility_bounds=str(session.plan.reproducibility_bounds),
            expected_contract=session.request.execution_contract.value,
            actual_contract=session.request.execution_contract.value,
            notes=(failure_reason,) if failure_reason else (),
        )
        if approximation is not None:
            calib_min, calib_max, calib_note = calibrate_scores(
                session.artifact.metric, results_buffer
            )
            approx_rank_instability = compute_rank_instability(
                results_buffer, witness_results
            )
            slo_met_latency = None
            nd_settings = session.request.nd_settings
            if nd_settings and nd_settings.latency_budget_ms is not None:
                slo_met_latency = cost.wall_time_estimate_ms <= float(
                    nd_settings.latency_budget_ms
                )
            slo_met_recall = None
            if (
                nd_settings
                and nd_settings.target_recall is not None
                and witness_report is not None
            ):
                slo_met_recall = witness_report.overlap_ratio >= float(
                    nd_settings.target_recall
                )
            notes = []
            if failure_reason in {"nd_no_confident_neighbors", "nd_low_signal_margin"}:
                notes.append("low_signal")
            if failure_reason == "nd_low_signal_refused":
                notes.append("low_signal_refused")
            if failure_reason == "nd_adaptive_k":
                notes.append("adaptive_k")
            if witness_report is None:
                notes.append("witness_not_measured")
            overlap_estimate = (
                witness_report.overlap_ratio if witness_report is not None else None
            )
            confidence_label = "medium_confidence"
            if failure_reason in {"nd_no_confident_neighbors", "nd_low_signal_refused"}:
                confidence_label = "low_confidence"
            elif (
                approx_rank_instability < 0.1
                and compute_distance_margin(results_buffer) > 0.01
            ):
                confidence_label = "high_confidence"
            approximation = replace(
                approximation,
                rank_instability=approx_rank_instability,
                distance_margin=compute_distance_margin(results_buffer),
                similarity_entropy=compute_similarity_entropy(results_buffer),
                witness_report=witness_report,
                calibrated_score_min=calib_min,
                calibrated_score_max=calib_max,
                calibration_note=calib_note,
                stability_signature=stability_signature(
                    session.artifact.metric, results_buffer
                ),
                overlap_estimate=overlap_estimate,
                confidence_label=confidence_label,
                low_signal_threshold=nd_settings.outlier_threshold
                if nd_settings is not None
                else None,
                adaptive_k_used=failure_reason == "nd_adaptive_k",
                low_signal=failure_reason == "nd_no_confident_neighbors",
                returned_k=len(results_buffer),
                slo_met_latency=slo_met_latency,
                slo_met_recall=slo_met_recall,
                degraded=failure_reason
                in {
                    "nd_adaptive_k",
                    "nd_no_confident_neighbors",
                    "nd_low_signal_margin",
                },
                degradation_reason=failure_reason,
                notes=tuple(notes),
            )
    execution_result = ExecutionResult(
        execution_id=session.execution.execution_id,
        signature=signature,
        artifact_id=session.artifact.artifact_id,
        plan=session.plan,
        results=tuple(results_buffer),
        cost=cost,
        approximation=approximation,
        nd_result=None,
        status=status,
        failure_reason=failure_reason,
        randomness_sources=randomness_sources,
        randomness_budget=randomness_budget,
        randomness_envelopes=randomness_envelopes,
        determinism_report=determinism_report,
    )
    if session.request.execution_contract is ExecutionContract.NON_DETERMINISTIC:
        quality_reason = None
        if execution_result.approximation is None:
            quality_reason = "quality_not_measured"
        nd_quality = execution_result.approximation
        nd_confidence = None
        if nd_quality is not None:
            nd_confidence = nd_quality.confidence_label
        execution_result = replace(
            execution_result,
            nd_result=NDResultSchema(
                results=execution_result.results,
                quality=nd_quality,
                quality_reason=quality_reason,
                confidence_label=nd_confidence,
                reproducibility_bounds=str(session.plan.reproducibility_bounds),
                refusal=failure_reason,
                decision_trace=decision_trace,
            ),
        )
    else:
        if execution_result.approximation is not None:
            raise InvariantError(
                message="Deterministic execution should not include approximation report"
            )
    return execution_result
