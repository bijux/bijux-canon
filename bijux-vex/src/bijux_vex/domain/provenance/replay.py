# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass

from bijux_vex.contracts.resources import ExecutionResources
from bijux_vex.core.canon import canon
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError, ReplayNotSupportedError
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.runtime.vector_execution import RandomnessProfile
from bijux_vex.core.types import ExecutionArtifact, ExecutionRequest, Result
from bijux_vex.domain.execution_requests.execute import (
    execute_request,
    start_execution_session,
)
from bijux_vex.infra.adapters.ann_base import AnnExecutionRequestRunner


@dataclass(frozen=True)
class ReplayOutcome:
    execution_contract: ExecutionContract
    execution_id: str
    original_fingerprint: str
    replay_fingerprint: str
    results: tuple[Result, ...]
    details: dict[str, str]
    nondeterministic_sources: tuple[str, ...] = ()

    @property
    def matches(self) -> bool:
        return self.original_fingerprint == self.replay_fingerprint


def _results_fingerprint(results: Iterable[Result]) -> str:
    payload = [canon(r).decode("utf-8") for r in results]
    return fingerprint(payload)


def replay(
    request: ExecutionRequest,
    artifact: ExecutionArtifact,
    resources: ExecutionResources,
    ann_runner: AnnExecutionRequestRunner | None = None,
    randomness: RandomnessProfile | None = None,
    baseline_fingerprint: str | None = None,
) -> ReplayOutcome:
    if request.execution_contract is not artifact.execution_contract:
        raise InvariantError(
            message="Execution contract does not match artifact execution contract",
            invariant_id="INV-010",
        )
    stored = resources.ledger.latest_execution_result(artifact.artifact_id)
    if stored is None:
        raise InvariantError(
            message="Replay requires existing provenance for artifact",
            invariant_id="INV-040",
        )
    nondeterministic_sources: tuple[str, ...] = ()
    original_fp = baseline_fingerprint or _results_fingerprint(stored.results)
    if artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC:
        if randomness is None:
            raise ReplayNotSupportedError(
                message="Non-deterministic replay requires randomness profile"
            )
        if randomness.non_replayable:
            raise ReplayNotSupportedError(
                message="Non-deterministic replay refused for non-replayable requests"
            )
        if randomness.seed is None:
            raise ReplayNotSupportedError(
                message="Non-deterministic replay requires a seed"
            )
        nondeterministic_sources = stored.plan.randomness_labels()
        if not nondeterministic_sources:
            raise InvariantError(
                message="Non-deterministic replay missing randomness annotations",
                invariant_id="INV-041",
            )
        if ann_runner is not None and hasattr(ann_runner, "index_info"):
            stored_hash = None
            if stored.approximation is not None:
                stored_hash = stored.approximation.index_hash
            current_info = ann_runner.index_info(artifact.artifact_id)
            current_hash = current_info.get("index_hash") if current_info else None
            if stored_hash and current_hash and stored_hash != current_hash:
                raise ReplayNotSupportedError(
                    message="Non-deterministic replay refused: ANN index hash mismatch"
                )
            if request.nd_settings and request.nd_settings.replay_strict:
                if stored.approximation is None:
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: missing approximation report"
                    )
                if not current_info:
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: missing ANN index info"
                    )
                stored_algo = stored.approximation.algorithm
                current_algo = current_info.get("index_kind")
                if stored_algo and current_algo and stored_algo != current_algo:
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: ANN algorithm mismatch"
                    )
                stored_backend = stored.approximation.backend_version
                current_backend = current_info.get("backend_version")
                if (
                    stored_backend
                    and current_backend
                    and stored_backend != current_backend
                ):
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: ANN backend version mismatch"
                    )
                stored_backend_name = stored.approximation.backend
                current_backend_name = current_info.get("backend")
                if (
                    stored_backend_name
                    and current_backend_name
                    and stored_backend_name != current_backend_name
                ):
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: ANN backend mismatch"
                    )
                stored_params = dict(stored.approximation.index_parameters)
                current_params = current_info.get("index_params", {})
                if stored_params and current_params and stored_params != current_params:
                    raise ReplayNotSupportedError(
                        message="Non-deterministic replay refused: ANN parameters mismatch"
                    )
        session = start_execution_session(
            artifact,
            request,
            resources,
            randomness=randomness,
            ann_runner=ann_runner,
        )
        fresh_execution, _ = execute_request(
            session,
            resources,
            ann_runner=ann_runner,
        )
        results = fresh_execution.results
        replay_fp = _results_fingerprint(results)
    else:
        if baseline_fingerprint is None:
            results = stored.results
            replay_fp = original_fp
        else:
            session = start_execution_session(
                artifact,
                request,
                resources,
                ann_runner=ann_runner,
            )
            fresh_execution, _ = execute_request(
                session,
                resources,
                ann_runner=ann_runner,
            )
            results = fresh_execution.results
            replay_fp = _results_fingerprint(results)
    details: dict[str, str] = {}
    if nondeterministic_sources:
        details["execution_contract"] = artifact.execution_contract.value
        details["replayability"] = "divergence allowed under non_deterministic contract"
        details["randomness_sources"] = ",".join(nondeterministic_sources)
    if original_fp != replay_fp:
        details["results_fingerprint"] = f"{original_fp} != {replay_fp}"
        details["replay_semantics"] = (
            "nondeterministic_divergence"
            if artifact.execution_contract is ExecutionContract.NON_DETERMINISTIC
            else "deterministic_mismatch"
        )
    return ReplayOutcome(
        execution_contract=artifact.execution_contract,
        execution_id=stored.execution_id,
        original_fingerprint=original_fp,
        replay_fingerprint=replay_fp,
        results=results,
        details=details,
        nondeterministic_sources=nondeterministic_sources,
    )
