# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Contracts for optional OpenAI-compatible remote embeddings."""

from __future__ import annotations

import urllib.parse
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from typing import Literal, Protocol

EndpointClass = Literal["public", "private", "local", "mock"]
FailureCategory = Literal[
    "authentication",
    "client",
    "protocol",
    "rate_limit",
    "server",
    "timeout",
    "transport",
]


@dataclass(frozen=True, slots=True)
class RemoteTimeouts:
    """Separate remote connection and response-read limits."""

    connect_seconds: float = 5.0
    read_seconds: float = 30.0

    def __post_init__(self) -> None:
        if self.connect_seconds <= 0 or self.read_seconds <= 0:
            raise ValueError("remote embedding timeouts must be positive")


@dataclass(frozen=True, slots=True)
class RemoteEmbeddingConfig:
    """Complete non-secret identity and resource policy for a remote endpoint."""

    endpoint: str
    endpoint_class: EndpointClass
    model: str
    dimension: int
    max_attempts: int = 3
    retry_backoff_seconds: float = 0.25
    timeouts: RemoteTimeouts = RemoteTimeouts()
    max_response_bytes: int = 16 * 1024 * 1024
    require_authentication: bool = True

    def __post_init__(self) -> None:
        parsed = urllib.parse.urlsplit(self.endpoint)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc:
            raise ValueError("remote embedding endpoint must be an absolute HTTP URL")
        if self.endpoint_class in {"public", "private"} and parsed.scheme != "https":
            raise ValueError("non-local remote embedding endpoints require HTTPS")
        if not self.model or self.dimension < 1:
            raise ValueError("remote embedding model and dimension are required")
        if self.max_attempts < 1 or self.max_attempts > 5:
            raise ValueError("remote embedding attempts must be within 1..5")
        if self.retry_backoff_seconds < 0:
            raise ValueError("remote embedding retry backoff must not be negative")
        if self.max_response_bytes < 1024:
            raise ValueError("remote embedding response limit is too small")


@dataclass(frozen=True, slots=True)
class RemoteHTTPResponse:
    """Transport-neutral HTTP response envelope."""

    status: int
    headers: Mapping[str, str]
    body: bytes


class RemoteEmbeddingTransport(Protocol):
    """Injected HTTP transport boundary."""

    def send(
        self,
        *,
        endpoint: str,
        headers: Mapping[str, str],
        body: bytes,
        timeouts: RemoteTimeouts,
        max_response_bytes: int,
    ) -> RemoteHTTPResponse:
        """Send one bounded request without interpreting its contents."""

        ...


class RemoteEmbeddingError(RuntimeError):
    """Classified remote failure suitable for retry and operator decisions."""

    def __init__(
        self,
        message: str,
        *,
        category: FailureCategory,
        retryable: bool,
        attempts: int,
        status: int | None = None,
    ) -> None:
        self.category = category
        self.retryable = retryable
        self.attempts = attempts
        self.status = status
        super().__init__(message)


@dataclass(frozen=True, slots=True)
class RemoteEmbeddingUsage:
    """Provider-reported token usage."""

    input_tokens: int
    total_tokens: int


@dataclass(frozen=True, slots=True)
class RemoteEmbeddingProvenance:
    """Auditable remote execution metadata without content or credentials."""

    endpoint_class: EndpointClass
    model: str
    attempts: int
    latency_ms: float
    request_sha256: str
    response_sha256: str
    provider_request_id: str | None
    usage: RemoteEmbeddingUsage


@dataclass(frozen=True, slots=True)
class RemoteEmbeddingBatch:
    """Stable ordered vectors and their remote execution provenance."""

    vectors: tuple[tuple[float, ...], ...]
    provenance: RemoteEmbeddingProvenance


CredentialProvider = Callable[[], str | None]
EventLogger = Callable[[Mapping[str, object]], None]
Clock = Callable[[], float]
Sleeper = Callable[[float], None]


__all__ = [
    "Clock",
    "CredentialProvider",
    "EndpointClass",
    "EventLogger",
    "FailureCategory",
    "RemoteEmbeddingBatch",
    "RemoteEmbeddingConfig",
    "RemoteEmbeddingError",
    "RemoteEmbeddingProvenance",
    "RemoteEmbeddingTransport",
    "RemoteEmbeddingUsage",
    "RemoteHTTPResponse",
    "RemoteTimeouts",
    "Sleeper",
]
