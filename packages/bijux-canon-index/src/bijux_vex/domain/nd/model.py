# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from collections.abc import Callable, Iterable
from dataclasses import dataclass, replace
import json
from pathlib import Path
from typing import Any

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import (
    AnnIndexBuildError,
    InvariantError,
    NDExecutionUnavailableError,
)
from bijux_vex.core.execution_mode import ExecutionMode
from bijux_vex.core.execution_result import NDDecisionTrace
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import (
    ExecutionArtifact,
    ExecutionBudget,
    ExecutionRequest,
    NDSettings,
)
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.domain.execution_requests.plan import build_execution_plan
from bijux_vex.domain.nd.randomness import require_randomness_for_nd
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner
from bijux_vex.infra.logging import log_event


@dataclass(frozen=True)
class NDPlan:
    runner: AnnExecutionRequestRunner
    settings: NDSettings | None
    budget: ExecutionBudget | None
    params: dict[str, object]
    reproducibility_bounds: str


class NDExecutionModel:
    """Central ND execution model for planning, execution, and verification."""

    def __init__(
        self,
        *,
        stores: ExecutionResources,
        ann_runner: AnnExecutionRequestRunner | None,
        latest_vector_fingerprint: str | None = None,
        tx_factory: Callable[[], Any] | None = None,
    ) -> None:
        self._stores = stores
        self._ann_runner = ann_runner
        self._latest_vector_fingerprint = latest_vector_fingerprint
        self._tx_factory = tx_factory

    def build_settings(self, req: object) -> NDSettings | None:
        nd_settings = NDSettings(
            profile=getattr(req, "nd_profile", None),
            target_recall=getattr(req, "nd_target_recall", None),
            latency_budget_ms=getattr(req, "nd_latency_budget_ms", None),
            witness_rate=getattr(req, "nd_witness_rate", None),
            witness_sample_k=getattr(req, "nd_witness_sample_k", None),
            witness_mode=getattr(req, "nd_witness_mode", None),
            build_on_demand=getattr(req, "nd_build_on_demand", False),
            candidate_k=getattr(req, "nd_candidate_k", None),
            diversity_lambda=getattr(req, "nd_diversity_lambda", None),
            normalize_vectors=getattr(req, "nd_normalize_vectors", False),
            normalize_query=getattr(req, "nd_normalize_query", False),
            outlier_threshold=getattr(req, "nd_outlier_threshold", None),
            low_signal_margin=getattr(req, "nd_low_signal_margin", None),
            adaptive_k=getattr(req, "nd_adaptive_k", False),
            low_signal_refuse=getattr(req, "nd_low_signal_refuse", False),
            replay_strict=getattr(req, "nd_replay_strict", False),
            warmup_queries=getattr(req, "nd_warmup_queries", None),
            incremental_index=getattr(req, "nd_incremental_index", None),
            max_candidates=getattr(req, "nd_max_candidates", None),
            max_index_memory_mb=getattr(req, "nd_max_index_memory_mb", None),
            two_stage=getattr(req, "nd_two_stage", True),
            m=getattr(req, "nd_m", None),
            ef_construction=getattr(req, "nd_ef_construction", None),
            ef_search=getattr(req, "nd_ef_search", None),
            max_ef_search=getattr(req, "nd_max_ef_search", None),
            space=getattr(req, "nd_space", None),
        )
        nd_fields = (
            "nd_profile",
            "nd_target_recall",
            "nd_latency_budget_ms",
            "nd_witness_rate",
            "nd_witness_sample_k",
            "nd_witness_mode",
            "nd_build_on_demand",
            "nd_candidate_k",
            "nd_diversity_lambda",
            "nd_normalize_vectors",
            "nd_normalize_query",
            "nd_outlier_threshold",
            "nd_low_signal_margin",
            "nd_adaptive_k",
            "nd_low_signal_refuse",
            "nd_replay_strict",
            "nd_warmup_queries",
            "nd_incremental_index",
            "nd_max_candidates",
            "nd_max_index_memory_mb",
            "nd_m",
            "nd_ef_construction",
            "nd_ef_search",
            "nd_max_ef_search",
            "nd_space",
        )
        has_nd_fields = any(
            getattr(req, field, None) not in (None, False) for field in nd_fields
        )
        if getattr(req, "nd_two_stage", True) is False:
            has_nd_fields = True
        if has_nd_fields:
            return nd_settings
        return None

    def plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        randomness: RandomnessProfile | None,
    ) -> NDPlan:
        if artifact.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
            raise InvariantError(
                message="ND execution requires non_deterministic artifact"
            )
        if request.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
            raise InvariantError(
                message="ND execution requires non_deterministic request"
            )
        if request.execution_mode is ExecutionMode.STRICT:
            raise InvariantError(message="ND execution cannot run in strict mode")
        if self._ann_runner is None:
            raise NDExecutionUnavailableError(
                message="ANN runner required for non_deterministic execution"
            )
        plan, execution = build_execution_plan(
            artifact,
            request,
            self._stores,
            randomness=randomness,
            ann_runner=self._ann_runner,
        )
        params = {
            "top_k": request.top_k,
            "metric": artifact.metric,
            "nd_profile": getattr(request.nd_settings, "profile", None)
            if request.nd_settings
            else None,
        }
        return NDPlan(
            runner=self._ann_runner,
            settings=request.nd_settings,
            budget=request.execution_budget,
            params=params,
            reproducibility_bounds=str(plan.reproducibility_bounds),
        )

    def ensure_index(
        self,
        artifact: ExecutionArtifact,
        nd_settings: NDSettings | None,
        build_on_demand: bool,
    ) -> ExecutionArtifact:
        ann_runner = self._ann_runner
        if ann_runner is None:
            raise NDExecutionUnavailableError(
                message="ANN runner required for non_deterministic execution"
            )
        index_info: dict[str, object] | None = None
        if hasattr(ann_runner, "index_info"):
            index_info = ann_runner.index_info(artifact.artifact_id)
        needs_build = artifact.index_state != "ready" or not index_info
        if needs_build:
            if (
                nd_settings is not None
                and nd_settings.incremental_index is False
                and not build_on_demand
            ):
                raise AnnIndexBuildError(
                    message="ANN index invalidated; rebuild required (incremental_index=false)"
                )
            if not build_on_demand:
                raise AnnIndexBuildError(
                    message="ANN index missing; run materialize --index-mode ann or set --nd-build-on-demand"
                )
            vectors = list(self._stores.vectors.list_vectors())
            index_info = ann_runner.build_index(
                artifact.artifact_id, vectors, artifact.metric, nd_settings
            )
            index_hash = index_info.get("index_hash") if index_info else None
            extra: tuple[tuple[str, str], ...] = (
                ("ann_index_info", json.dumps(index_info, sort_keys=True)),
            )
            if index_hash:
                extra = extra + (("ann_index_hash", str(index_hash)),)
            artifact = replace(
                artifact,
                build_params=artifact.build_params + extra,
                index_state="ready",
            )
            if self._tx_factory is None:
                raise InvariantError(message="ND model missing tx_factory")
            with self._tx_factory() as tx:
                self._stores.ledger.put_artifact(tx, artifact)
        return artifact

    def validate_index_invariants(self, artifact: ExecutionArtifact) -> None:
        if artifact.execution_contract is not ExecutionContract.NON_DETERMINISTIC:
            return
        if artifact.index_state != "ready":
            return
        ann_runner = self._ann_runner
        ann_info = (
            ann_runner.index_info(artifact.artifact_id)
            if ann_runner is not None and hasattr(ann_runner, "index_info")
            else None
        )
        build_params = dict(artifact.build_params)
        stored_hash = build_params.get("ann_index_hash")
        current_hash = ann_info.get("index_hash") if ann_info else None
        if stored_hash and current_hash and stored_hash != str(current_hash):
            raise AnnIndexBuildError(message="ANN index drift detected (hash mismatch)")
        if (
            self._latest_vector_fingerprint
            and self._latest_vector_fingerprint != artifact.vector_fingerprint
        ):
            raise AnnIndexBuildError(
                message="ANN index drift detected (vector fingerprint mismatch)"
            )
        if ann_info and "vector_count" in ann_info:
            current_count = sum(1 for _ in self._stores.vectors.list_vectors())
            count_value = ann_info.get("vector_count")
            if isinstance(count_value, bool):
                count = 0
            elif isinstance(count_value, (int, float, str)):
                try:
                    count = int(count_value)
                except ValueError:
                    count = 0
            else:
                count = 0
            if count != int(current_count):
                raise AnnIndexBuildError(
                    message="ANN index drift detected (vector count mismatch)"
                )

    def warmup(
        self, artifact: ExecutionArtifact, nd_settings: NDSettings | None
    ) -> None:
        if nd_settings is None or nd_settings.warmup_queries is None:
            return
        ann_runner = self._ann_runner
        if ann_runner is None or not hasattr(ann_runner, "warmup"):
            return
        try:
            warmup_payload = json.loads(Path(nd_settings.warmup_queries).read_text())
            if isinstance(warmup_payload, list):
                ann_runner.warmup(
                    artifact.artifact_id,
                    (
                        tuple(item)
                        for item in warmup_payload
                        if isinstance(item, (list, tuple))
                    ),
                )
        except Exception:
            log_event("nd_warmup_failed", path=str(nd_settings.warmup_queries))

    def execute(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        randomness: RandomnessProfile | None,
        build_on_demand: bool,
    ) -> tuple[Any, Iterable[Any]]:
        session = self._stage_plan(
            artifact, request, randomness, build_on_demand=build_on_demand
        )
        plan = self.plan(artifact, request, randomness)
        decision_trace = NDDecisionTrace(
            runner=type(plan.runner).__name__,
            params=tuple(sorted(plan.params.items())),
            budget=tuple(sorted(_budget_items(plan.budget))),
            refusal=None,
            degradation=None,
            notes=(),
        )
        results_iter = self._stage_execute(session, decision_trace)
        execution_result, results = self._stage_verify(results_iter)
        execution_result = self._stage_postprocess(execution_result, decision_trace)
        return execution_result, results

    def _stage_plan(
        self,
        artifact: ExecutionArtifact,
        request: ExecutionRequest,
        randomness: RandomnessProfile | None,
        *,
        build_on_demand: bool,
    ) -> Any:
        session = start_execution_session(
            artifact, request, self._stores, randomness, self._ann_runner
        )
        require_randomness_for_nd(session, self._ann_runner)
        artifact = self.ensure_index(artifact, request.nd_settings, build_on_demand)
        self.validate_index_invariants(artifact)
        self.warmup(artifact, request.nd_settings)
        return session

    def _stage_execute(
        self, session: Any, decision_trace: NDDecisionTrace
    ) -> tuple[Any, Iterable[Any]]:
        return execute_request(
            session,
            self._stores,
            ann_runner=self._ann_runner,
            decision_trace=decision_trace,
        )

    def _stage_verify(
        self, execution_outcome: tuple[Any, Iterable[Any]]
    ) -> tuple[Any, Iterable[Any]]:
        return execution_outcome

    def _stage_postprocess(
        self, execution_result: Any, decision_trace: NDDecisionTrace
    ) -> Any:
        if execution_result.nd_result is None:
            return execution_result
        return replace(
            execution_result,
            nd_result=replace(
                execution_result.nd_result, decision_trace=decision_trace
            ),
        )

    def decision_trace_from_request(
        self, request: ExecutionRequest, refusal: str | None = None
    ) -> NDDecisionTrace:
        params: dict[str, object] = {"top_k": request.top_k}
        if request.nd_settings:
            params.update(
                {
                    "profile": request.nd_settings.profile,
                    "candidate_k": request.nd_settings.candidate_k,
                    "ef_search": request.nd_settings.ef_search,
                }
            )
        return NDDecisionTrace(
            runner=type(self._ann_runner).__name__ if self._ann_runner else "none",
            params=tuple(sorted(params.items())),
            budget=tuple(sorted(_budget_items(request.execution_budget))),
            refusal=refusal,
            degradation=None,
            notes=(),
        )


def _budget_items(budget: ExecutionBudget | None) -> Iterable[tuple[str, object]]:
    if budget is None:
        return ()
    values = {
        "max_latency_ms": budget.max_latency_ms,
        "max_memory_mb": budget.max_memory_mb,
        "max_error": budget.max_error,
        "max_vectors": budget.max_vectors,
        "max_distance_computations": budget.max_distance_computations,
        "max_ann_probes": budget.max_ann_probes,
    }
    return tuple(sorted((k, v) for k, v in values.items() if v is not None))
