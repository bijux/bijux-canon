# SPDX-License-Identifier: MIT
# Copyright © 2025 Bijan Mousavi
from __future__ import annotations

from collections.abc import Iterable
import json

from bijux_vex.core.contracts.execution_contract import ExecutionContract
from bijux_vex.core.errors import InvariantError
from bijux_vex.core.types import ExecutionArtifact

ALLOWED_METRICS = {"l2", "cosine", "dot"}


def _require(condition: bool, message: str) -> None:
    if not condition:
        raise InvariantError(message=message)


def _is_json_safe(params: Iterable[tuple[str, str]]) -> bool:
    try:
        json.dumps(list(params), ensure_ascii=True)
    except Exception:
        return False
    return True


def validate_execution_artifact(artifact: ExecutionArtifact) -> None:
    _require(artifact.schema_version == "v1", "Unsupported ExecutionArtifact version")
    _require(
        isinstance(artifact.execution_contract, ExecutionContract),
        "execution_contract must be provided",
    )
    _require(bool(artifact.corpus_fingerprint), "corpus_fingerprint must be non-empty")
    _require(bool(artifact.vector_fingerprint), "vector_fingerprint must be non-empty")
    _require(bool(artifact.scoring_version), "scoring_version must be non-empty")
    _require(
        artifact.metric in ALLOWED_METRICS,
        f"metric must be one of {sorted(ALLOWED_METRICS)}",
    )
    _require(
        _is_json_safe(artifact.build_params),
        "build_params must be JSON-canonicalizable",
    )
    _require(
        len(artifact.build_params) <= 256,
        "build_params exceed growth limits for artifacts",
    )
    _require(
        len(str(artifact.build_params)) <= 8192,
        "build_params payload too large for artifact",
    )
    expected_replayable = artifact.execution_contract is ExecutionContract.DETERMINISTIC
    _require(
        artifact.replayable is expected_replayable,
        "replayable must follow execution_contract",
    )
    _require(bool(artifact.execution_id), "execution_id must be present")
