# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from dataclasses import dataclass, field

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.identity.ids import fingerprint


@dataclass(frozen=True)
class RandomnessSource:
    name: str
    description: str
    category: str  # e.g. sampling, graph_traversal, parallelism


@dataclass(frozen=True)
class ExecutionPlan:
    algorithm: str
    contract: ExecutionContract
    k: int
    scoring_fn: str
    randomness_sources: tuple[RandomnessSource, ...] = field(default_factory=tuple)
    reproducibility_bounds: str = ""
    steps: tuple[str, ...] = field(default_factory=tuple)
    fingerprint: str = field(init=False)

    def randomness_labels(self) -> tuple[str, ...]:
        return tuple(src.name for src in self.randomness_sources)

    def __post_init__(self) -> None:
        if not isinstance(self.contract, ExecutionContract):
            raise InvariantError(
                message="ExecutionPlan requires an execution contract enum"
            )
        payload = (
            self.algorithm,
            self.contract.value,
            self.k,
            self.scoring_fn,
            tuple((s.name, s.description, s.category) for s in self.randomness_sources),
            self.reproducibility_bounds,
            self.steps,
        )
        object.__setattr__(self, "fingerprint", fingerprint(payload))


__all__ = ["ExecutionPlan", "RandomnessSource"]
