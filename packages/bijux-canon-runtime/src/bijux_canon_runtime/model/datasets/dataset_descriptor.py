# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for model/datasets/dataset_descriptor.py."""

from __future__ import annotations

from dataclasses import dataclass

from bijux_canon_runtime.spec.ontology import DatasetState
from bijux_canon_runtime.spec.ontology.ids import DatasetID, TenantID


@dataclass(frozen=True)
class DatasetDescriptor:
    """Dataset descriptor; misuse breaks dataset governance."""

    spec_version: str
    dataset_id: DatasetID
    tenant_id: TenantID
    dataset_version: str
    dataset_hash: str
    dataset_state: DatasetState
    storage_uri: str


__all__ = ["DatasetDescriptor"]
