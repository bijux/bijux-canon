# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Retrying, secret-safe OpenAI-compatible embedding client."""

from __future__ import annotations

from collections.abc import Sequence
import hashlib
import http.client
import json
import math
import time

from .contracts import (
    Clock,
    CredentialProvider,
    EventLogger,
    FailureCategory,
    RemoteEmbeddingBatch,
    RemoteEmbeddingConfig,
    RemoteEmbeddingError,
    RemoteEmbeddingProvenance,
    RemoteEmbeddingTransport,
    RemoteEmbeddingUsage,
    RemoteHTTPResponse,
    Sleeper,
)


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256(value: bytes) -> str:
    return f"sha256:{hashlib.sha256(value).hexdigest()}"


def _classify_status(status: int, attempts: int) -> RemoteEmbeddingError:
    if status in {401, 403}:
        return RemoteEmbeddingError(
            "remote embedding authentication failed",
            category="authentication",
            retryable=False,
            attempts=attempts,
            status=status,
        )
    if status == 429:
        category: FailureCategory = "rate_limit"
        retryable = True
    elif status == 408 or status >= 500:
        category = "server"
        retryable = True
    else:
        category = "client"
        retryable = False
    return RemoteEmbeddingError(
        f"remote embedding request failed with HTTP {status}",
        category=category,
        retryable=retryable,
        attempts=attempts,
        status=status,
    )


class RemoteEmbeddingClient:
    """OpenAI-compatible embedding port with bounded, secret-safe execution."""

    def __init__(
        self,
        config: RemoteEmbeddingConfig,
        *,
        transport: RemoteEmbeddingTransport,
        credential_provider: CredentialProvider = lambda: None,
        event_logger: EventLogger = lambda _event: None,
        clock: Clock = time.perf_counter,
        sleeper: Sleeper = time.sleep,
    ) -> None:
        self.config = config
        self._transport = transport
        self._credential_provider = credential_provider
        self._event_logger = event_logger
        self._clock = clock
        self._sleeper = sleeper

    def embed(self, texts: Sequence[str]) -> RemoteEmbeddingBatch:
        """Embed complete non-empty texts while preserving caller order."""

        values = tuple(texts)
        if not values or any(not isinstance(text, str) or not text for text in values):
            raise ValueError("remote embedding input must contain non-empty strings")
        credential = self._credential_provider()
        if self.config.require_authentication and not credential:
            raise RemoteEmbeddingError(
                "remote embedding credential is unavailable",
                category="authentication",
                retryable=False,
                attempts=0,
            )
        body = _canonical_json(
            {
                "encoding_format": "float",
                "input": list(values),
                "model": self.config.model,
            }
        )
        request_sha256 = _sha256(body)
        headers = {"Content-Type": "application/json"}
        if credential:
            headers["Authorization"] = f"Bearer {credential}"
        started = self._clock()
        last_error: RemoteEmbeddingError | None = None
        for attempt in range(1, self.config.max_attempts + 1):
            try:
                response = self._transport.send(
                    endpoint=self.config.endpoint,
                    headers=headers,
                    body=body,
                    timeouts=self.config.timeouts,
                    max_response_bytes=self.config.max_response_bytes,
                )
            except TimeoutError as error:
                last_error = RemoteEmbeddingError(
                    "remote embedding request timed out",
                    category="timeout",
                    retryable=True,
                    attempts=attempt,
                )
                cause: Exception = error
            except (OSError, http.client.HTTPException) as error:
                last_error = RemoteEmbeddingError(
                    "remote embedding transport failed",
                    category="transport",
                    retryable=True,
                    attempts=attempt,
                )
                cause = error
            except ValueError as error:
                last_error = RemoteEmbeddingError(
                    f"remote embedding transport response is invalid: {error}",
                    category="protocol",
                    retryable=False,
                    attempts=attempt,
                )
                cause = error
            else:
                if 200 <= response.status < 300:
                    return self._parse_success(
                        values,
                        response,
                        attempt=attempt,
                        latency_ms=(self._clock() - started) * 1000.0,
                        request_sha256=request_sha256,
                    )
                last_error = _classify_status(response.status, attempt)
                cause = last_error
            self._event_logger(
                {
                    "attempt": attempt,
                    "category": last_error.category,
                    "endpoint_class": self.config.endpoint_class,
                    "event": "remote_embedding_attempt_failed",
                    "model": self.config.model,
                    "request_sha256": request_sha256,
                    "retryable": last_error.retryable,
                    "status": last_error.status,
                }
            )
            if not last_error.retryable or attempt == self.config.max_attempts:
                raise last_error from cause
            self._sleeper(self.config.retry_backoff_seconds * attempt)
        raise AssertionError("remote embedding retry loop did not terminate")

    def _parse_success(
        self,
        texts: tuple[str, ...],
        response: RemoteHTTPResponse,
        *,
        attempt: int,
        latency_ms: float,
        request_sha256: str,
    ) -> RemoteEmbeddingBatch:
        response_sha256 = _sha256(response.body)
        try:
            payload = json.loads(response.body)
            if not isinstance(payload, dict):
                raise TypeError
            response_model = payload.get("model")
            if response_model is not None and response_model != self.config.model:
                raise ValueError("remote embedding response model mismatch")
            data = payload["data"]
            if not isinstance(data, list):
                raise TypeError
            indexed: dict[int, tuple[float, ...]] = {}
            for item in data:
                if not isinstance(item, dict) or not isinstance(item.get("index"), int):
                    raise TypeError
                vector_value = item.get("embedding")
                if not isinstance(vector_value, list):
                    raise TypeError
                vector = tuple(float(value) for value in vector_value)
                if (
                    len(vector) != self.config.dimension
                    or any(not math.isfinite(value) for value in vector)
                    or item["index"] in indexed
                ):
                    raise ValueError("remote embedding vector shape is invalid")
                indexed[item["index"]] = vector
            if set(indexed) != set(range(len(texts))):
                raise ValueError("remote embedding response order is incomplete")
            usage_value = payload.get("usage", {})
            if not isinstance(usage_value, dict):
                raise TypeError
            input_tokens = int(usage_value.get("prompt_tokens", 0))
            total_tokens = int(usage_value.get("total_tokens", input_tokens))
            if input_tokens < 0 or total_tokens < input_tokens:
                raise ValueError("remote embedding usage is invalid")
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise RemoteEmbeddingError(
                f"remote embedding response is invalid: {error}",
                category="protocol",
                retryable=False,
                attempts=attempt,
                status=response.status,
            ) from error
        provenance = RemoteEmbeddingProvenance(
            endpoint_class=self.config.endpoint_class,
            model=self.config.model,
            attempts=attempt,
            latency_ms=latency_ms,
            request_sha256=request_sha256,
            response_sha256=response_sha256,
            provider_request_id=response.headers.get("x-request-id"),
            usage=RemoteEmbeddingUsage(input_tokens, total_tokens),
        )
        self._event_logger(
            {
                "attempts": attempt,
                "endpoint_class": self.config.endpoint_class,
                "event": "remote_embedding_completed",
                "latency_ms": latency_ms,
                "model": self.config.model,
                "request_sha256": request_sha256,
                "response_sha256": response_sha256,
                "status": response.status,
            }
        )
        return RemoteEmbeddingBatch(
            vectors=tuple(indexed[index] for index in range(len(texts))),
            provenance=provenance,
        )


__all__ = ["RemoteEmbeddingClient"]
