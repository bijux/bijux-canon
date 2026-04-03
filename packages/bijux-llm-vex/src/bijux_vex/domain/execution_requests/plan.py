# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.determinism import classify_execution
from bijux_vex.core.errors import (
    BackendCapabilityError,
    InvariantError,
    NDExecutionUnavailableError,
    ValidationError,
)
from bijux_vex.core.runtime.execution_plan import ExecutionPlan, RandomnessSource
from bijux_vex.core.runtime.vector_execution import RandomnessProfile, VectorExecution
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, Result
from bijux_vex.domain.execution_algorithms import algorithms
from bijux_vex.domain.execution_algorithms.base import get_algorithm
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


def build_execution_plan(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    resources: ExecutionResources,
    randomness: RandomnessProfile | None = None,
    ann_runner: AnnExecutionRequestRunner | None = None,
) -> tuple[ExecutionPlan, VectorExecution]:
    _validate_contract_alignment(artifact, request)
    _validate_capabilities(artifact, request, resources)
    classify_execution(
        contract=request.execution_contract,
        randomness=randomness,
        ann_runner=ann_runner,
        vector_store=None,
    )
    plan, algo_name, randomness_profile = (
        _build_deterministic_plan(artifact, request)
        if request.execution_contract is ExecutionContract.DETERMINISTIC
        else _build_nd_plan(artifact, request, ann_runner, randomness)
    )
    execution = VectorExecution(
        request=request,
        contract=request.execution_contract,
        backend_id=resources.name,
        algorithm=algo_name,
        plan=plan,
        parameters=(("top_k", request.top_k), ("metric", artifact.metric)),
        randomness=randomness_profile,
    )
    return plan, execution


def run_plan(
    plan: ExecutionPlan,
    execution: VectorExecution,
    artifact: ExecutionArtifact,
    resources: ExecutionResources,
    ann_runner: AnnExecutionRequestRunner | None = None,
    budget: dict[str, int | float] | None = None,
) -> Iterable[Result]:
    if plan is None or execution is None:  # pragma: no cover - defensive
        raise InvariantError(
            message="run_plan requires an execution plan and execution context"
        )
    # Ensure plan immutability: recompute fingerprint and reject tampering.
    canonical_payload = (
        plan.algorithm,
        plan.contract.value,
        plan.k,
        plan.scoring_fn,
        tuple((s.name, s.description, s.category) for s in plan.randomness_sources),
        plan.reproducibility_bounds,
        plan.steps,
    )
    from bijux_vex.core.identity.ids import fingerprint as _fp

    if plan.fingerprint != _fp(canonical_payload):
        raise InvariantError(
            message="ExecutionPlan fingerprint mismatch; plan mutated or rebuilt",
            invariant_id="INV-030",
        )
    if execution.contract is ExecutionContract.DETERMINISTIC:
        algo = get_algorithm(algorithms.ExactVectorExecutionAlgorithm.name)
        if budget and budget.get("max_vectors") is not None:
            total_vectors = len(tuple(resources.vectors.list_vectors()))
            if total_vectors > int(budget["max_vectors"]):
                raise InvariantError(
                    message="Budget would be exceeded before deterministic execution begins"
                )
        return algo.execute(execution, artifact, resources.vectors)
    if ann_runner is None:
        capability = None
        if resources.capabilities:
            capability = "supports_ann" if resources.capabilities.supports_ann else None
        raise NDExecutionUnavailableError(
            message="Non-deterministic execution requested without ANN support",
            capability=capability,
            retryable=False,
        )
    if (
        budget
        and budget.get("max_ann_probes") is not None
        and int(budget["max_ann_probes"]) <= 0
    ):
        raise InvariantError(
            message="ANN probes budget exhausted before execution",
            invariant_id="INV-021",
        )
    algo = algorithms.build_ann_algorithm(ann_runner)
    return algo.execute(execution, artifact, resources.vectors)


__all__ = ["ExecutionPlan", "build_execution_plan", "run_plan"]


def _validate_contract_alignment(
    artifact: ExecutionArtifact, request: ExecutionRequest
) -> None:
    if request.execution_contract is not artifact.execution_contract:
        raise ValidationError(
            message="Backend resources reject mismatched execution contract",
            invariant_id="INV-010",
        )


def _validate_capabilities(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    resources: ExecutionResources,
) -> None:
    caps = resources.capabilities
    if not caps:
        return
    if caps.contracts and request.execution_contract not in caps.contracts:
        raise BackendCapabilityError(
            message="Backend does not support requested execution contract",
            invariant_id="INV-011",
        )
    if caps.metrics and artifact.metric not in caps.metrics:
        raise BackendCapabilityError(
            message="Backend does not support requested metric", invariant_id="INV-011"
        )
    if (
        request.execution_contract is ExecutionContract.DETERMINISTIC
        and caps.deterministic_query is False
    ):
        raise BackendCapabilityError(
            message="Backend refuses deterministic execution", invariant_id="INV-011"
        )
    if request.execution_contract is ExecutionContract.NON_DETERMINISTIC and (
        caps.ann_support is False or caps.supports_ann is False
    ):
        raise BackendCapabilityError(
            message="Backend refuses approximate execution", invariant_id="INV-011"
        )
    if (
        caps.replayable is False
        and artifact.execution_contract is ExecutionContract.DETERMINISTIC
    ):
        raise ValidationError(
            message="Backend replayability required but missing", invariant_id="INV-011"
        )
    if (
        request.vector is not None
        and caps.max_vector_size is not None
        and len(request.vector) > caps.max_vector_size
    ):
        raise ValidationError(
            message="Vector dimension exceeds backend capability",
            invariant_id="INV-011",
        )


def _build_deterministic_plan(
    artifact: ExecutionArtifact, request: ExecutionRequest
) -> tuple[ExecutionPlan, str, RandomnessProfile | None]:
    randomness_sources: tuple[RandomnessSource, ...] = ()
    reproducibility = "bit-identical"
    steps = ("plan_deterministic", "score_exact")
    plan = ExecutionPlan(
        algorithm=algorithms.ExactVectorExecutionAlgorithm.name,
        contract=request.execution_contract,
        k=request.top_k,
        scoring_fn=artifact.metric,
        randomness_sources=randomness_sources,
        reproducibility_bounds=reproducibility,
        steps=steps,
    )
    return plan, algorithms.ExactVectorExecutionAlgorithm.name, None


def _build_nd_plan(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    ann_runner: AnnExecutionRequestRunner | None,
    randomness: RandomnessProfile | None,
) -> tuple[ExecutionPlan, str, RandomnessProfile | None]:
    if ann_runner is None:
        raise NDExecutionUnavailableError(
            message="ANN runner required for non-deterministic execution"
        )
    randomness_sources = tuple(
        RandomnessSource(
            name=source,
            description=source,
            category="sampling",
        )
        for source in ann_runner.randomness_sources
    )
    reproducibility = _nd_reproducibility_bounds(
        artifact, request, randomness, ann_runner
    )
    steps: tuple[str, ...] = ("plan_nondeterministic", "execute_ann")
    if request.nd_settings is None or request.nd_settings.two_stage:
        steps = ("plan_nondeterministic", "execute_ann", "rescore_exact")
    plan = ExecutionPlan(
        algorithm="ann_approximate",
        contract=request.execution_contract,
        k=request.top_k,
        scoring_fn=artifact.metric,
        randomness_sources=randomness_sources,
        reproducibility_bounds=reproducibility,
        steps=steps,
    )
    return plan, "ann_approximate", randomness


def _nd_reproducibility_bounds(
    artifact: ExecutionArtifact,
    request: ExecutionRequest,
    randomness: RandomnessProfile | None,
    ann_runner: AnnExecutionRequestRunner,
) -> str:
    seed = randomness.seed if randomness else None
    non_replayable = randomness.non_replayable if randomness else False
    bounds = [
        f"backend={ann_runner.reproducibility_bounds}",
        f"index_hash={artifact.index_config_fingerprint}",
        f"seed={seed}",
        f"non_replayable={non_replayable}",
    ]
    if request.nd_settings:
        bounds.append(f"profile={request.nd_settings.profile}")
        bounds.append(f"target_recall={request.nd_settings.target_recall}")
        bounds.append(f"latency_budget_ms={request.nd_settings.latency_budget_ms}")
    return ";".join(str(item) for item in bounds if item is not None)
