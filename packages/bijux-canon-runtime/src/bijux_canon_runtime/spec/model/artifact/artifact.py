# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Module definitions for spec/model/artifact/artifact.py."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

from bijux_canon_runtime.spec.ontology import (
    ArtifactScope,
    ArtifactType,
)
from bijux_canon_runtime.spec.ontology.ids import ArtifactID, ContentHash, TenantID


@dataclass(frozen=True)
class Artifact:
    """Immutable artifact record; misuse breaks provenance."""

    spec_version: str
    artifact_id: ArtifactID
    tenant_id: TenantID
    artifact_type: ArtifactType
    producer: Literal["agent", "retrieval", "reasoning"]
    parent_artifacts: tuple[ArtifactID, ...]
    content_hash: ContentHash
    scope: ArtifactScope


__all__ = ["Artifact"]
