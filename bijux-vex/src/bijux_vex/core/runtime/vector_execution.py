# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import asdict, dataclass, field

from bijux_vex.core.canon import canon
from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.identity.ids import fingerprint
from bijux_vex.core.runtime.execution_plan import ExecutionPlan
from bijux_vex.core.types import ExecutionRequest


@dataclass(frozen=True)
class RandomnessProfile:
    seed: int | None = None
    sources: tuple[str, ...] = field(default_factory=tuple)
    bounded: bool = False
    non_replayable: bool = False
    budget: dict[str, int | float] | None = None
    envelopes: tuple[tuple[str, float], ...] = ()


@dataclass(frozen=True)
class VectorExecution:
    request: ExecutionRequest
    contract: ExecutionContract
    backend_id: str
    algorithm: str
    plan: ExecutionPlan | None = None
    parameters: tuple[tuple[str, object], ...] = field(default_factory=tuple)
    randomness: RandomnessProfile | None = None
    execution_id: str = field(init=False)

    def __post_init__(self) -> None:
        if (
            self.contract is ExecutionContract.NON_DETERMINISTIC
            and self.randomness is None
        ):
            raise InvariantError(
                message="RandomnessProfile required for non-deterministic execution"
            )
        request_payload = _canonical_request_payload(self.request)
        payload = {
            "request": request_payload,
            "contract": self.contract.value,
            "backend_id": self.backend_id,
            "algorithm": self.algorithm,
            "plan": canon(self.plan).decode("utf-8") if self.plan else None,
            "parameters": tuple(self.parameters),
            "randomness": tuple(self.randomness.sources) if self.randomness else (),
            "seed": self.randomness.seed if self.randomness else None,
            "bounded": self.randomness.bounded if self.randomness else False,
            "budget": tuple(sorted((self.randomness.budget or {}).items()))
            if self.randomness
            else (),
            "envelopes": self.randomness.envelopes if self.randomness else (),
        }
        if self.randomness:
            payload["non_replayable"] = self.randomness.non_replayable
        object.__setattr__(self, "execution_id", fingerprint(payload))


def derive_execution_id(
    request: ExecutionRequest,
    backend_id: str,
    algorithm: str,
    randomness: RandomnessProfile | None = None,
    plan: ExecutionPlan | None = None,
) -> str:
    if (
        randomness is None
        and request.execution_contract is ExecutionContract.NON_DETERMINISTIC
    ):
        randomness = RandomnessProfile(
            seed=0, sources=("execution_artifact",), bounded=True
        )
    execution = VectorExecution(
        request=request,
        contract=request.execution_contract,
        backend_id=backend_id,
        algorithm=algorithm,
        plan=plan,
        randomness=randomness,
        parameters=(),
    )
    return execution.execution_id


def execution_signature(
    plan: ExecutionPlan,
    corpus_fingerprint: str,
    vector_fingerprint: str,
    randomness: RandomnessProfile | None,
) -> str:
    payload = {
        "plan": canon(plan).decode("utf-8"),
        "corpus_fingerprint": corpus_fingerprint,
        "vector_fingerprint": vector_fingerprint,
        "randomness": tuple(randomness.sources) if randomness else (),
        "seed": randomness.seed if randomness else None,
    }
    if randomness:
        payload["non_replayable"] = randomness.non_replayable
    return fingerprint(payload)


def _canonical_request_payload(request: ExecutionRequest) -> str:
    payload = asdict(request)
    if payload.get("nd_settings") is None:
        payload.pop("nd_settings", None)
    return canon(payload).decode("utf-8")


__all__ = [
    "VectorExecution",
    "RandomnessProfile",
    "derive_execution_id",
    "execution_signature",
]
