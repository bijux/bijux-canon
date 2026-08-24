# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Typed contracts for the shared Runtime application boundary."""

from __future__ import annotations

from dataclasses import dataclass
from enum import StrEnum

from bijux_canon_runtime.ontology.ids import RequestID
from bijux_canon_runtime.runtime.replay.models import RuntimeReplayPolicy


class ApplicationOperation(StrEnum):
    """Stable operations exposed identically to library and transports."""

    CORPUS = "corpus.prepare"
    CORPUS_INSPECT = "corpus.inspect"
    ARTIFACT_PAYLOAD = "artifact.payload"
    INDEX = "index.build"
    INDEX_INSPECT = "index.inspect"
    RETRIEVE = "retrieve"
    RETRIEVAL_EVALUATE = "retrieval.evaluate"
    ASK = "ask"
    RESEARCH = "research"
    RUN = "run"
    INSPECT = "inspect"
    REPLAY = "replay"
    COMPARE = "compare"
    STATUS = "status"
    RESULT = "result"
    CANCEL = "cancel"


@dataclass(frozen=True, slots=True)
class ReplayOperationRequest:
    """Complete authority needed to create one linked replay attempt."""

    run_id: str
    source_attempt_id: str
    request_id: RequestID
    process_id: str
    policy: RuntimeReplayPolicy

    def __post_init__(self) -> None:
        if not self.run_id.strip():
            raise ValueError("replay run identity must not be empty")
        if not self.source_attempt_id.strip():
            raise ValueError("replay source attempt identity must not be empty")
        if not str(self.request_id).strip():
            raise ValueError("replay request identity must not be empty")
        if not self.process_id.strip():
            raise ValueError("replay process identity must not be empty")


@dataclass(frozen=True, slots=True)
class RuntimeApplicationCapability:
    """Machine-readable identity of the shared application contract."""

    schema_version: str
    service_version: str
    operations: tuple[ApplicationOperation, ...]
    asynchronous_operations: tuple[ApplicationOperation, ...]

    def __post_init__(self) -> None:
        if self.schema_version != "bijux.runtime.application-capability.v2":
            raise ValueError("application capability schema is unsupported")
        if self.service_version != "2.0":
            raise ValueError("application service version is unsupported")
        if tuple(self.operations) != tuple(ApplicationOperation):
            raise ValueError("application capability must declare every operation")
        expected_async = (
            ApplicationOperation.CORPUS,
            ApplicationOperation.INDEX,
            ApplicationOperation.RETRIEVE,
            ApplicationOperation.ASK,
            ApplicationOperation.RESEARCH,
            ApplicationOperation.RUN,
            ApplicationOperation.REPLAY,
        )
        if self.asynchronous_operations != expected_async:
            raise ValueError("application asynchronous operation set is incomplete")


__all__ = [
    "ApplicationOperation",
    "ReplayOperationRequest",
    "RuntimeApplicationCapability",
]
