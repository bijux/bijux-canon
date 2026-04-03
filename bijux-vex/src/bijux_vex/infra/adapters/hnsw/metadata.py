# SPDX-License-Identifier: MIT
# Copyright © 2026 Bijan Mousavi
from __future__ import annotations

from bijux_vex.core.errors import CorruptArtifactError, InvariantError
from bijux_vex.core.types import ExecutionArtifact, NDSettings
from bijux_vex.infra.adapters.hnsw.params import as_int, resolve_space


def as_dict(value: object) -> dict[str, object]:
    if isinstance(value, dict):
        return value
    return {}


def validate_index_meta(
    artifact: ExecutionArtifact,
    meta: dict[str, object],
    settings: NDSettings | None,
    *,
    index_version: int,
) -> None:
    if not meta:
        raise CorruptArtifactError(message="ANN index metadata missing")
    if meta.get("artifact_id") != artifact.artifact_id:
        raise CorruptArtifactError(message="ANN index metadata artifact mismatch")
    if meta.get("metric") != artifact.metric:
        raise CorruptArtifactError(message="ANN index metadata metric mismatch")
    if as_int(meta.get("index_version"), 0) != index_version:
        raise CorruptArtifactError(message="ANN index version mismatch")
    if as_int(meta.get("dimension"), 0) <= 0:
        raise CorruptArtifactError(message="ANN index dimension missing")
    params = as_dict(meta.get("index_params"))
    if settings and settings.space:
        space = resolve_space(artifact.metric, settings.space)
        if meta.get("space") not in (None, space):
            raise InvariantError(message="ANN index space mismatch")
    if (
        settings
        and settings.m is not None
        and as_int(params.get("M"), 0) != int(settings.m)
    ):
        raise InvariantError(message="ANN index M parameter mismatch")
    if (
        settings
        and settings.ef_construction is not None
        and as_int(params.get("ef_construction"), 0) != int(settings.ef_construction)
    ):
        raise InvariantError(message="ANN index ef_construction mismatch")
    if (
        settings
        and settings.ef_search is not None
        and as_int(params.get("ef_search"), 0) != int(settings.ef_search)
    ):
        raise InvariantError(message="ANN index ef_search mismatch")
    if (
        settings
        and settings.max_ef_search is not None
        and as_int(params.get("ef_search"), 0) > int(settings.max_ef_search)
    ):
        raise InvariantError(message="ANN index max_ef_search exceeded")
    if settings and settings.space and meta.get("space") != settings.space:
        raise InvariantError(message="ANN index space mismatch")
