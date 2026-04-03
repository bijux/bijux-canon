# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import BudgetExceededError
from bijux_vex.core.execution_result import (
    ApproximationReport,
    ExecutionCost,
    ExecutionStatus,
)
from bijux_vex.core.runtime.execution_session import (
    ExecutionSession,
    ExecutionState,
    enforce_transition,
)
from bijux_vex.core.types import ExecutionRequest, Result
from bijux_vex.domain.execution_requests.budget import check_budget
from bijux_vex.domain.execution_requests.plan import run_plan
from bijux_vex.domain.execution_requests.scoring import tie_break_key
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.logging import log_event


def collect_results(
    session: ExecutionSession,
    resources: ExecutionResources,
    ann_runner: AnnExecutionRequestRunner | None,
) -> tuple[list[Result], ExecutionStatus, str | None, ApproximationReport | None]:
    enforce_transition(session.state, ExecutionState.RUNNING)
    counters = {"vectors": 0, "distance": 0, "ann_probes": 0}
    results_buffer: list[Result] = []
    status = ExecutionStatus.SUCCESS
    failure_reason: str | None = None
    approximation: ApproximationReport | None = None
    try:
        _preflight_budget(session.budget)
        results_iter = run_plan(
            session.plan,
            session.execution,
            session.artifact,
            resources,
            ann_runner=ann_runner,
            budget=session.budget,
        )
    except BudgetExceededError as exc:
        failure_reason = _budget_failure_reason(exc)
        status = ExecutionStatus.PARTIAL
        if (
            ann_runner is not None
            and session.request.execution_contract
            is ExecutionContract.NON_DETERMINISTIC
        ):
            approximation = ann_runner.approximation_report(
                session.artifact, session.request, ()
            )
        return results_buffer, status, failure_reason, approximation
    try:
        for res in results_iter:
            counters["vectors"] += 1
            counters["distance"] += 1
            if ann_runner is not None:
                counters["ann_probes"] += 1
            check_budget(session.budget, counters, results_buffer)
            results_buffer.append(res)
        if (
            session.request.execution_contract is ExecutionContract.NON_DETERMINISTIC
            and session.request.nd_settings is not None
        ):
            from bijux_vex.domain.execution_requests.nd_quality import (
                adaptive_filter_results,
            )

            results_buffer, degraded, low_signal = adaptive_filter_results(
                session.artifact.metric,
                results_buffer,
                session.request.nd_settings.outlier_threshold,
                session.request.nd_settings.adaptive_k,
            )
            if (
                session.request.nd_settings.low_signal_margin is not None
                and results_buffer
            ):
                from bijux_vex.domain.execution_requests.nd_quality import (
                    compute_distance_margin,
                )

                margin = compute_distance_margin(results_buffer)
                if margin < float(session.request.nd_settings.low_signal_margin):
                    low_signal = True
                    if not degraded:
                        failure_reason = "nd_low_signal_margin"
            if degraded:
                status = ExecutionStatus.PARTIAL
                failure_reason = "nd_adaptive_k"
                log_event(
                    "nd_degraded",
                    reason="adaptive_k",
                    returned_k=len(results_buffer),
                    requested_k=session.request.top_k,
                )
            if low_signal:
                signal_reason = failure_reason or "nd_low_signal"
                if session.request.nd_settings.low_signal_refuse:
                    results_buffer = []
                    status = ExecutionStatus.FAILED
                    failure_reason = "nd_low_signal_refused"
                    log_event(
                        "nd_low_signal_refused",
                        reason=signal_reason,
                        requested_k=session.request.top_k,
                    )
                else:
                    status = ExecutionStatus.PARTIAL
                    failure_reason = "nd_no_confident_neighbors"
                    log_event(
                        "nd_low_signal",
                        reason=signal_reason,
                        returned_k=len(results_buffer),
                        requested_k=session.request.top_k,
                    )
        if session.request.execution_contract is ExecutionContract.NON_DETERMINISTIC:
            results_buffer.sort(key=tie_break_key)
            for idx, res in enumerate(results_buffer, start=1):
                results_buffer[idx - 1] = Result(
                    request_id=res.request_id,
                    document_id=res.document_id,
                    chunk_id=res.chunk_id,
                    vector_id=res.vector_id,
                    artifact_id=res.artifact_id,
                    score=res.score,
                    rank=idx,
                )
        if (
            ann_runner is not None
            and session.request.execution_contract
            is ExecutionContract.NON_DETERMINISTIC
        ):
            approximation = ann_runner.approximation_report(
                session.artifact, session.request, tuple(results_buffer)
            )
    except BudgetExceededError as exc:
        failure_reason = _budget_failure_reason(exc)
        status = ExecutionStatus.PARTIAL
        from typing import cast

        if getattr(exc, "partial_results", None):
            results_buffer = list(cast(Iterable[Result], exc.partial_results))
        if (
            ann_runner is not None
            and session.request.execution_contract
            is ExecutionContract.NON_DETERMINISTIC
        ):
            approximation = ann_runner.approximation_report(
                session.artifact, session.request, tuple(results_buffer)
            )
    except Exception as exc:  # pragma: no cover - unexpected path
        failure_reason = _budget_failure_reason(exc)
        if failure_reason:
            status = ExecutionStatus.PARTIAL
        else:
            raise
    return results_buffer, status, failure_reason, approximation


def _preflight_budget(budget: dict[str, int | float] | None) -> None:
    if not budget:
        return
    if budget.get("max_vectors") is not None and int(budget["max_vectors"]) <= 0:
        raise BudgetExceededError(
            message="max vectors budget exhausted",
            dimension="vectors",
            partial_results=(),
        )
    if (
        budget.get("max_distance_computations") is not None
        and int(budget["max_distance_computations"]) <= 0
    ):
        raise BudgetExceededError(
            message="distance budget exhausted",
            dimension="distance",
            partial_results=(),
        )
    if budget.get("max_ann_probes") is not None and int(budget["max_ann_probes"]) <= 0:
        raise BudgetExceededError(
            message="ANN probes budget exhausted",
            dimension="ann_probes",
            partial_results=(),
        )
    if budget.get("max_latency_ms") is not None and int(budget["max_latency_ms"]) <= 0:
        raise BudgetExceededError(
            message="latency budget exhausted",
            dimension="latency",
            partial_results=(),
        )
    if budget.get("max_memory_mb") is not None and int(budget["max_memory_mb"]) <= 0:
        raise BudgetExceededError(
            message="memory budget exhausted",
            dimension="memory",
            partial_results=(),
        )


def _budget_failure_reason(exc: Exception) -> str | None:
    if hasattr(exc, "dimension"):
        return f"budget_exhausted_{exc.dimension}"
    return None


def estimate_cost(
    request: ExecutionRequest, results_buffer: Iterable[Result]
) -> ExecutionCost:
    result_list = list(results_buffer)
    vector_ops = len(result_list) * (len(request.vector) if request.vector else 1)
    return ExecutionCost(
        vector_reads=len(result_list),
        distance_computations=len(result_list),
        graph_hops=0
        if request.execution_contract is ExecutionContract.DETERMINISTIC
        else len(result_list),
        wall_time_estimate_ms=float(len(result_list)),
        cpu_time_ms=float(len(result_list)),
        memory_estimate_mb=float(len(result_list)) / 10.0,
        vector_ops=vector_ops,
    )
