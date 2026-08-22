# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Hash-bound development and held-out evaluation access control."""

from __future__ import annotations

from enum import StrEnum
from typing import Self

from pydantic import field_validator, model_validator

from bijux_canon_reason.core.models.base import StableModel
from bijux_canon_reason.evaluation.truth import EvaluationSplit, Sha256
from bijux_canon_reason.grounding.provider_contracts import (
    content_artifact_id,
    require_artifact_id,
)


class EvaluationAccessPurpose(StrEnum):
    """Declared reason for reading an evaluation partition."""

    tuning = "tuning"
    configuration = "configuration"
    prompt_selection = "prompt-selection"
    evaluation = "evaluation"


class EvaluationPartitionIdentities(StableModel):
    """Frozen identities of development and held-out inputs and labels."""

    development_inputs_sha256: Sha256
    development_labels_sha256: Sha256
    heldout_inputs_sha256: Sha256
    heldout_labels_sha256: Sha256


class EvaluationAccessRecord(StableModel):
    """One authorized content-addressed partition access."""

    artifact_id: str
    access_id: str
    split: EvaluationSplit
    purpose: EvaluationAccessPurpose
    inputs_sha256: Sha256
    labels_sha256: Sha256 | None

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("evaluation access identity does not match")
        return self


class EvaluationResultRecord(StableModel):
    """Result identity bound to one completed evaluation access."""

    artifact_id: str
    access_artifact_id: str
    result_sha256: Sha256

    @field_validator("artifact_id", "access_artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_identity(self) -> Self:
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("evaluation result record identity does not match")
        return self


class HeldoutIsolationReport(StableModel):
    """Restart-safe complete access and result ledger."""

    schema_version: str = "bijux.canon.evaluation.heldout-isolation.v1"
    artifact_id: str
    partition_identities: EvaluationPartitionIdentities
    accesses: tuple[EvaluationAccessRecord, ...]
    results: tuple[EvaluationResultRecord, ...]
    passed: bool

    @field_validator("artifact_id")
    @classmethod
    def _validate_artifact_id(cls, value: str) -> str:
        return require_artifact_id(value)

    @model_validator(mode="after")
    def _validate_report(self) -> Self:
        access_ids = {item.artifact_id for item in self.accesses}
        if len(access_ids) != len(self.accesses):
            raise ValueError("evaluation accesses must be unique")
        if len({item.access_id for item in self.accesses}) != len(self.accesses):
            raise ValueError("evaluation access IDs must be unique")
        result_access_ids = {item.access_artifact_id for item in self.results}
        if len(result_access_ids) != len(self.results):
            raise ValueError("each evaluation access may have only one result")
        if not result_access_ids.issubset(access_ids):
            raise ValueError("evaluation result references an unknown access")
        required_results = {
            item.artifact_id
            for item in self.accesses
            if item.purpose is EvaluationAccessPurpose.evaluation
        }
        expected_pass = required_results == result_access_ids
        if self.passed != expected_pass:
            raise ValueError("held-out isolation completion status is inconsistent")
        payload = self.model_dump(mode="json", exclude={"artifact_id"})
        if self.artifact_id != content_artifact_id(payload):
            raise ValueError("held-out isolation report identity does not match")
        return self


class HeldoutIsolationError(ValueError):
    """An access would expose held-out material to tuning or is incomplete."""


class HeldoutIsolationLedger:
    """Authorize partition access and bind every evaluation result."""

    def __init__(self, identities: EvaluationPartitionIdentities) -> None:
        self._identities = identities
        self._accesses: list[EvaluationAccessRecord] = []
        self._results: list[EvaluationResultRecord] = []

    def authorize(
        self,
        *,
        access_id: str,
        split: EvaluationSplit,
        purpose: EvaluationAccessPurpose,
        labels_requested: bool,
    ) -> EvaluationAccessRecord:
        """Create an access record only when held-out isolation permits it."""
        if any(item.access_id == access_id for item in self._accesses):
            raise HeldoutIsolationError("evaluation access ID already exists")
        if (
            split is EvaluationSplit.heldout
            and purpose is not EvaluationAccessPurpose.evaluation
        ):
            raise HeldoutIsolationError(
                "held-out inputs and labels cannot be used for tuning, configuration, or prompt selection"
            )
        inputs_sha256, labels_sha256 = self._partition_hashes(split)
        payload = {
            "access_id": access_id,
            "split": split.value,
            "purpose": purpose.value,
            "inputs_sha256": inputs_sha256,
            "labels_sha256": labels_sha256 if labels_requested else None,
        }
        access = EvaluationAccessRecord(
            artifact_id=content_artifact_id(payload),
            access_id=access_id,
            split=split,
            purpose=purpose,
            inputs_sha256=inputs_sha256,
            labels_sha256=labels_sha256 if labels_requested else None,
        )
        self._accesses.append(access)
        return access

    def record_result(
        self, *, access_artifact_id: str, result_sha256: str
    ) -> EvaluationResultRecord:
        """Bind a result identity to one authorized evaluation access."""
        access = next(
            (item for item in self._accesses if item.artifact_id == access_artifact_id),
            None,
        )
        if access is None:
            raise HeldoutIsolationError("evaluation result references unknown access")
        if access.purpose is not EvaluationAccessPurpose.evaluation:
            raise HeldoutIsolationError(
                "only evaluation access produces a result record"
            )
        if any(item.access_artifact_id == access_artifact_id for item in self._results):
            raise HeldoutIsolationError("evaluation result is already recorded")
        payload = {
            "access_artifact_id": access_artifact_id,
            "result_sha256": result_sha256,
        }
        result = EvaluationResultRecord(
            artifact_id=content_artifact_id(payload),
            access_artifact_id=access_artifact_id,
            result_sha256=result_sha256,
        )
        self._results.append(result)
        return result

    def report(self) -> HeldoutIsolationReport:
        """Return the complete ledger; incomplete evaluations remain failed."""
        required = {
            item.artifact_id
            for item in self._accesses
            if item.purpose is EvaluationAccessPurpose.evaluation
        }
        completed = {item.access_artifact_id for item in self._results}
        passed = required == completed
        payload = {
            "schema_version": "bijux.canon.evaluation.heldout-isolation.v1",
            "partition_identities": self._identities.model_dump(mode="json"),
            "accesses": tuple(item.model_dump(mode="json") for item in self._accesses),
            "results": tuple(item.model_dump(mode="json") for item in self._results),
            "passed": passed,
        }
        return HeldoutIsolationReport(
            artifact_id=content_artifact_id(payload),
            partition_identities=self._identities,
            accesses=tuple(self._accesses),
            results=tuple(self._results),
            passed=passed,
        )

    def _partition_hashes(self, split: EvaluationSplit) -> tuple[str, str]:
        if split is EvaluationSplit.development:
            return (
                self._identities.development_inputs_sha256,
                self._identities.development_labels_sha256,
            )
        return (
            self._identities.heldout_inputs_sha256,
            self._identities.heldout_labels_sha256,
        )


__all__ = [
    "EvaluationAccessPurpose",
    "EvaluationAccessRecord",
    "EvaluationPartitionIdentities",
    "EvaluationResultRecord",
    "HeldoutIsolationError",
    "HeldoutIsolationLedger",
    "HeldoutIsolationReport",
]
