# SPDX-License-Identifier: Apache-2.0
# Copyright © 2025 Bijan Mousavi

"""Module definitions for spec/contracts/dataset_contract.py."""

from __future__ import annotations

from agentic_flows.spec.model.datasets.dataset_descriptor import DatasetDescriptor
from agentic_flows.spec.ontology import DatasetState

_ALLOWED_TRANSITIONS: dict[DatasetState, set[DatasetState]] = {
    DatasetState.EXPERIMENTAL: {
        DatasetState.EXPERIMENTAL,
        DatasetState.FROZEN,
        DatasetState.DEPRECATED,
    },
    DatasetState.FROZEN: {DatasetState.FROZEN, DatasetState.DEPRECATED},
    DatasetState.DEPRECATED: {DatasetState.DEPRECATED},
}


def validate_dataset_descriptor(dataset: DatasetDescriptor) -> None:
    """Validate dataset descriptor; misuse breaks dataset governance."""
    if not isinstance(dataset.dataset_state, DatasetState):
        raise ValueError("dataset_state must be a DatasetState")
    if not isinstance(dataset.storage_uri, str) or not dataset.storage_uri.strip():
        raise ValueError("dataset.storage_uri must be a non-empty string")


def validate_transition(
    previous: DatasetState | None, next_state: DatasetState
) -> None:
    """Validate dataset transition; misuse breaks state integrity."""
    if previous is None:
        return
    allowed = _ALLOWED_TRANSITIONS.get(previous, set())
    if next_state not in allowed:
        raise ValueError(
            f"dataset_state transition from {previous.value} to {next_state.value} is not allowed"
        )


__all__ = ["validate_dataset_descriptor", "validate_transition"]
