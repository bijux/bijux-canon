# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

from collections.abc import Iterator, Mapping
from contextlib import contextmanager
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
import threading

import pytest

from bijux_canon_index.infra.embeddings.remote import (
    RemoteEmbeddingClient,
    RemoteEmbeddingConfig,
    RemoteEmbeddingError,
    RemoteEmbeddingTransport,
    RemoteHTTPResponse,
    RemoteTimeouts,
    StandardLibraryEmbeddingTransport,
)


@contextmanager
def _mock_server(
    responses: list[tuple[int, dict[str, object]]],
) -> Iterator[tuple[str, list[dict[str, object]]]]:
    observed: list[dict[str, object]] = []

    class Handler(BaseHTTPRequestHandler):
        def do_POST(self) -> None:  # noqa: N802
            length = int(self.headers["content-length"])
            observed.append(
                {
                    "authorization": self.headers.get("authorization"),
                    "body": json.loads(self.rfile.read(length)),
                    "path": self.path,
                }
            )
            status, payload = responses.pop(0)
            body = json.dumps(payload, sort_keys=True).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("X-Request-ID", f"mock-{len(observed)}")
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, _format: str, *_args: object) -> None:
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_port}/v1/embeddings", observed
    finally:
        server.shutdown()
        server.server_close()
        thread.join()


def _success_payload() -> dict[str, object]:
    return {
        "data": [
            {"embedding": [0.0, 1.0], "index": 1},
            {"embedding": [1.0, 0.0], "index": 0},
        ],
        "model": "remote-model",
        "usage": {"prompt_tokens": 7, "total_tokens": 7},
    }


def _config(endpoint: str, *, max_attempts: int = 3) -> RemoteEmbeddingConfig:
    return RemoteEmbeddingConfig(
        endpoint=endpoint,
        endpoint_class="mock",
        model="remote-model",
        dimension=2,
        max_attempts=max_attempts,
        retry_backoff_seconds=0.0,
        timeouts=RemoteTimeouts(connect_seconds=1.0, read_seconds=1.0),
    )


def test_remote_embedding_uses_mock_server_and_logs_only_safe_provenance() -> None:
    secret = "super-secret-token"
    texts = ("protected research alpha", "protected research beta")
    events: list[Mapping[str, object]] = []
    with _mock_server([(200, _success_payload())]) as (endpoint, observed):
        client = RemoteEmbeddingClient(
            _config(endpoint),
            transport=StandardLibraryEmbeddingTransport(),
            credential_provider=lambda: secret,
            event_logger=events.append,
        )

        batch = client.embed(texts)

    assert batch.vectors == ((1.0, 0.0), (0.0, 1.0))
    assert batch.provenance.provider_request_id == "mock-1"
    assert batch.provenance.usage.input_tokens == 7
    assert batch.provenance.usage.total_tokens == 7
    assert batch.provenance.request_sha256.startswith("sha256:")
    assert batch.provenance.response_sha256.startswith("sha256:")
    assert observed[0]["authorization"] == f"Bearer {secret}"
    assert observed[0]["body"] == {
        "encoding_format": "float",
        "input": list(texts),
        "model": "remote-model",
    }
    logged = json.dumps(events)
    assert secret not in logged
    assert all(text not in logged for text in texts)


def test_remote_embedding_retries_rate_limit_with_bounded_attempts() -> None:
    sleeps: list[float] = []
    with _mock_server([(429, {"error": "busy"}), (200, _success_payload())]) as (
        endpoint,
        observed,
    ):
        client = RemoteEmbeddingClient(
            _config(endpoint, max_attempts=2),
            transport=StandardLibraryEmbeddingTransport(),
            credential_provider=lambda: "credential",
            sleeper=sleeps.append,
        )

        batch = client.embed(("first", "second"))

    assert batch.provenance.attempts == 2
    assert len(observed) == 2
    assert sleeps == [0.0]


class _SequenceTransport(RemoteEmbeddingTransport):
    def __init__(self, outcomes: list[RemoteHTTPResponse | Exception]) -> None:
        self.outcomes = outcomes
        self.calls = 0

    def send(
        self,
        *,
        endpoint: str,
        headers: Mapping[str, str],
        body: bytes,
        timeouts: RemoteTimeouts,
        max_response_bytes: int,
    ) -> RemoteHTTPResponse:
        self.calls += 1
        outcome = self.outcomes.pop(0)
        if isinstance(outcome, Exception):
            raise outcome
        return outcome


def test_remote_embedding_classifies_exhausted_timeout() -> None:
    transport = _SequenceTransport([TimeoutError(), TimeoutError()])
    client = RemoteEmbeddingClient(
        _config("http://127.0.0.1/embeddings", max_attempts=2),
        transport=transport,
        credential_provider=lambda: "credential",
        sleeper=lambda _: None,
    )

    with pytest.raises(RemoteEmbeddingError) as raised:
        client.embed(("text",))

    assert raised.value.category == "timeout"
    assert raised.value.retryable is True
    assert raised.value.attempts == 2
    assert transport.calls == 2


def test_remote_embedding_does_not_retry_authentication_failure() -> None:
    response = RemoteHTTPResponse(401, {}, b'{"error":"unauthorized"}')
    transport = _SequenceTransport([response])
    client = RemoteEmbeddingClient(
        _config("http://127.0.0.1/embeddings"),
        transport=transport,
        credential_provider=lambda: "credential",
    )

    with pytest.raises(RemoteEmbeddingError) as raised:
        client.embed(("text",))

    assert raised.value.category == "authentication"
    assert raised.value.retryable is False
    assert raised.value.status == 401
    assert transport.calls == 1


def test_remote_embedding_enforces_response_dimension() -> None:
    payload = {
        "data": [{"embedding": [1.0], "index": 0}],
        "model": "remote-model",
    }
    transport = _SequenceTransport(
        [RemoteHTTPResponse(200, {}, json.dumps(payload).encode())]
    )
    client = RemoteEmbeddingClient(
        _config("http://127.0.0.1/embeddings"),
        transport=transport,
        credential_provider=lambda: "credential",
    )

    with pytest.raises(RemoteEmbeddingError) as raised:
        client.embed(("text",))

    assert raised.value.category == "protocol"
    assert raised.value.retryable is False


def test_remote_embedding_requires_https_outside_local_endpoints() -> None:
    with pytest.raises(ValueError, match="HTTPS"):
        RemoteEmbeddingConfig(
            endpoint="http://example.test/v1/embeddings",
            endpoint_class="public",
            model="remote-model",
            dimension=2,
        )
