# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from typing import Literal, cast

from pydantic import Field, model_validator

from bijux_canon_reason.core.fingerprints import stable_id
from bijux_canon_reason.core.models.base import JsonValue, StableModel


class ProblemSpec(StableModel):
    id: str = ""
    description: str
    constraints: dict[str, object] = Field(default_factory=dict)
    expected_output_type: str = "Claim"
    expected: dict[str, object] | None = None
    version: int | None = None

    def with_content_id(self) -> ProblemSpec:
        cid = stable_id(
            "spec",
            {
                "description": self.description,
                "constraints": self.constraints,
                "expected_output_type": self.expected_output_type,
                "expected": self.expected,
                "version": self.version,
            },
        )
        return self.model_copy(update={"id": cid})

    @model_validator(mode="after")
    def _ensure_id(self) -> ProblemSpec:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "spec",
                    {
                        "description": self.description,
                        "constraints": self.constraints,
                        "expected_output_type": self.expected_output_type,
                        "expected": self.expected,
                        "version": self.version,
                    },
                ),
            )
        return self


StepKind = Literal["understand", "gather", "derive", "verify", "finalize"]


class ToolRequest(StableModel):
    tool_name: str
    arguments: dict[str, JsonValue] = Field(default_factory=dict)


class StepSpec(StableModel):
    kind: StepKind
    notes: str = ""
    tool_requests: list[ToolRequest] = Field(default_factory=list)


class PlanNode(StableModel):
    id: str = ""
    kind: StepKind
    dependencies: list[str] = Field(default_factory=list)
    step: StepSpec
    parameters: dict[str, JsonValue] = Field(default_factory=dict)

    @model_validator(mode="before")
    @classmethod
    def _default_step(cls, values: dict[str, object]) -> dict[str, object]:
        if "step" not in values and "kind" in values:
            kind = cast(StepKind, values["kind"])
            values["step"] = StepSpec(kind=kind)
        return values

    @model_validator(mode="after")
    def _fill_id(self) -> PlanNode:
        if not self.id:
            object.__setattr__(
                self,
                "id",
                stable_id(
                    "node",
                    {
                        "kind": self.kind,
                        "deps": self.dependencies,
                        "params": self.parameters,
                        "step": self.step.model_dump(mode="json"),
                    },
                ),
            )
        return self


class Plan(StableModel):
    id: str = ""
    problem: str = ""
    spec_id: str
    nodes: list[PlanNode] = Field(default_factory=list)
    edges: list[tuple[str, str]] = Field(default_factory=list)

    def with_content_id(self) -> Plan:
        cid = stable_id(
            "plan",
            {
                "problem": self.problem,
                "spec_id": self.spec_id,
                "nodes": [node.model_dump(mode="json") for node in self.nodes],
                "edges": self.edges,
            },
        )
        return self.model_copy(update={"id": cid})


__all__ = [
    "Plan",
    "PlanNode",
    "ProblemSpec",
    "StepKind",
    "StepSpec",
    "ToolRequest",
]
