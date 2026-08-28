# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Immutable content-addressed storage for VEX execution artifacts."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict, dataclass, field
from enum import Enum
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import cast

from .policy import VexPolicyDecision
from .witnesses import ExactSearchWitness

_ARTIFACT_ID = re.compile(r"^sha256:([0-9a-f]{64})$")


def _json_value(value: object) -> object:
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, list | tuple):
        return [_json_value(item) for item in value]
    return value


def _canonical_json(value: object) -> str:
    return json.dumps(
        _json_value(value),
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    )


def _sha256_json(value: object) -> str:
    return hashlib.sha256(_canonical_json(value).encode("utf-8")).hexdigest()


def _canonical_mapping(value: Mapping[str, object]) -> dict[str, object]:
    normalized = json.loads(_canonical_json(value))
    if not isinstance(normalized, dict):
        raise ValueError("VEX artifact sections must be JSON objects")
    return cast(dict[str, object], normalized)


def _execution_identity_payload(
    request: object,
    normalized_vector_sha256: object,
    plan: object,
) -> dict[str, object]:
    return {
        "normalized_vector_sha256": normalized_vector_sha256,
        "plan": plan,
        "request": request,
    }


@dataclass(frozen=True, slots=True)
class VexCandidateRecord:
    """One persisted candidate in declared execution order."""

    source: str
    rank: int
    score: float
    chunk_id: str

    def __post_init__(self) -> None:
        if not self.source or not self.chunk_id or self.rank <= 0:
            raise ValueError("VEX candidates require source, chunk ID, and rank")


@dataclass(frozen=True, slots=True)
class VexExecutionArtifact:
    """Complete immutable inputs, outputs, policy, logs, and component hashes."""

    request: Mapping[str, object]
    normalized_vector_sha256: str
    plan: Mapping[str, object]
    candidates: tuple[VexCandidateRecord, ...]
    witness: ExactSearchWitness
    metrics: Mapping[str, object]
    decision: VexPolicyDecision
    logs: tuple[str, ...]
    schema_version: str = "bijux.canon.vex.execution_artifact.v1"
    execution_id: str = field(init=False)
    artifact_id: str = field(init=False)
    component_hashes: Mapping[str, str] = field(init=False)

    def __post_init__(self) -> None:
        if not re.fullmatch(r"[0-9a-f]{64}", self.normalized_vector_sha256):
            raise ValueError("VEX normalized vector identity must be a SHA-256 digest")
        object.__setattr__(self, "request", _canonical_mapping(self.request))
        object.__setattr__(self, "plan", _canonical_mapping(self.plan))
        object.__setattr__(self, "metrics", _canonical_mapping(self.metrics))
        object.__setattr__(self, "candidates", tuple(self.candidates))
        object.__setattr__(self, "logs", tuple(self.logs))
        if not self.logs:
            raise ValueError("VEX execution artifacts require execution logs")
        sections = {
            "request": self.request,
            "normalized_vector": self.normalized_vector_sha256,
            "plan": self.plan,
            "candidates": [asdict(candidate) for candidate in self.candidates],
            "witness": asdict(self.witness),
            "metrics": self.metrics,
            "decision": asdict(self.decision),
            "logs": self.logs,
        }
        hashes = {key: _sha256_json(value) for key, value in sections.items()}
        object.__setattr__(self, "component_hashes", hashes)
        identity = _execution_identity_payload(
            self.request,
            self.normalized_vector_sha256,
            self.plan,
        )
        object.__setattr__(self, "execution_id", f"sha256:{_sha256_json(identity)}")
        object.__setattr__(
            self, "artifact_id", f"sha256:{_sha256_json(self.payload())}"
        )

    def payload(self) -> dict[str, object]:
        """Return canonical artifact content, excluding its derived artifact ID."""

        return {
            "artifact_type": "bijux.canon.vex.execution",
            "candidate_order": [asdict(candidate) for candidate in self.candidates],
            "component_hashes": dict(self.component_hashes),
            "decision": asdict(self.decision),
            "execution_id": self.execution_id,
            "logs": list(self.logs),
            "metrics": dict(self.metrics),
            "normalized_vector_sha256": self.normalized_vector_sha256,
            "plan": dict(self.plan),
            "request": dict(self.request),
            "schema_version": self.schema_version,
            "witness": asdict(self.witness),
        }

    def record(self) -> dict[str, object]:
        """Return the stored record with its derived content address."""

        return {"artifact_id": self.artifact_id, **self.payload()}


@dataclass(frozen=True, slots=True)
class VexStoredArtifact:
    """Verified bytes and decoded payload returned by the artifact store."""

    artifact_id: str
    content_sha256: str
    byte_length: int
    record: Mapping[str, object]


class VexArtifactStore:
    """Persistent immutable store keyed by canonical execution artifact content."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root).resolve()
        self.root.mkdir(parents=True, exist_ok=True)

    def put(self, artifact: VexExecutionArtifact) -> VexStoredArtifact:
        """Persist one artifact without overwriting an existing content address."""

        record = artifact.record()
        raw = (_canonical_json(record) + "\n").encode("utf-8")
        destination = self._path(artifact.artifact_id)
        destination.parent.mkdir(parents=True, exist_ok=True)
        if destination.exists():
            if destination.read_bytes() != raw:
                raise ValueError(
                    "VEX artifact content address is occupied by other bytes"
                )
            return self.load(artifact.artifact_id)
        descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{destination.name}.",
            suffix=".writing",
            dir=destination.parent,
        )
        temporary = Path(temporary_name)
        try:
            with os.fdopen(descriptor, "wb") as handle:
                handle.write(raw)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(temporary, destination)
            except FileExistsError:
                if destination.read_bytes() != raw:
                    raise ValueError(
                        "VEX artifact content address raced with other bytes"
                    ) from None
            directory_descriptor = os.open(destination.parent, os.O_RDONLY)
            try:
                os.fsync(directory_descriptor)
            finally:
                os.close(directory_descriptor)
        finally:
            temporary.unlink(missing_ok=True)
        return self.load(artifact.artifact_id)

    def load(self, artifact_id: str) -> VexStoredArtifact:
        """Load and verify canonical bytes, content address, and component hashes."""

        path = self._path(artifact_id)
        raw = path.read_bytes()
        try:
            record = json.loads(raw)
        except (UnicodeDecodeError, json.JSONDecodeError) as error:
            raise ValueError("VEX artifact is unreadable") from error
        if not isinstance(record, dict):
            raise ValueError("VEX artifact record must be a JSON object")
        canonical = (_canonical_json(record) + "\n").encode("utf-8")
        if raw != canonical:
            raise ValueError("VEX artifact is not canonical JSON")
        stored_id = record.get("artifact_id")
        payload = dict(record)
        payload.pop("artifact_id", None)
        expected_id = f"sha256:{_sha256_json(payload)}"
        if stored_id != artifact_id or expected_id != artifact_id:
            raise ValueError("VEX artifact content address does not match its payload")
        execution_identity = _execution_identity_payload(
            record.get("request"),
            record.get("normalized_vector_sha256"),
            record.get("plan"),
        )
        expected_execution_id = f"sha256:{_sha256_json(execution_identity)}"
        if record.get("execution_id") != expected_execution_id:
            raise ValueError(
                "VEX execution identity does not match its immutable inputs"
            )
        hashes = record.get("component_hashes")
        if not isinstance(hashes, dict):
            raise ValueError("VEX artifact component hashes are missing")
        component_values = {
            "request": record.get("request"),
            "normalized_vector": record.get("normalized_vector_sha256"),
            "plan": record.get("plan"),
            "candidates": record.get("candidate_order"),
            "witness": record.get("witness"),
            "metrics": record.get("metrics"),
            "decision": record.get("decision"),
            "logs": record.get("logs"),
        }
        if hashes != {
            key: _sha256_json(value) for key, value in component_values.items()
        }:
            raise ValueError("VEX artifact component hash mismatch")
        return VexStoredArtifact(
            artifact_id=artifact_id,
            content_sha256=hashlib.sha256(raw).hexdigest(),
            byte_length=len(raw),
            record=record,
        )

    def _path(self, artifact_id: str) -> Path:
        match = _ARTIFACT_ID.fullmatch(artifact_id)
        if match is None:
            raise ValueError("VEX artifact ID must be content-addressed")
        digest = match.group(1)
        return self.root / "objects" / "sha256" / digest[:2] / f"{digest}.json"


__all__ = [
    "VexArtifactStore",
    "VexCandidateRecord",
    "VexExecutionArtifact",
    "VexStoredArtifact",
]
