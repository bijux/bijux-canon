# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Structured provider contract, retry, repair, and mock-server tests."""

from __future__ import annotations

from contextlib import contextmanager
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from threading import Thread
from typing import Iterator

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    CandidateOutcome,
    CitationEvidence,
    EvidencePacketBuilder,
    EvidencePacketPolicy,
    ImmutableEvidenceLocator,
    JsonHttpResponse,
    OpenAICompatibleStructuredSynthesizer,
    ProviderAttemptKind,
    ProviderAttemptStatus,
    StructuredProviderConfiguration,
    StructuredProviderError,
    StructuredProviderErrorCode,
    StructuredProviderPolicy,
    StructuredProviderSynthesis,
    prompt_artifact_id,
    response_schema_sha256,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _artifact(value: str) -> str:
    return f"sha256:{_sha(value)}"


def _packet():
    text = "The admitted study reports a source-scoped ancient DNA observation."
    evidence = CitationEvidence(
        artifact_id=_artifact("evidence"),
        chunk_artifact_id=_artifact("chunk"),
        retrieval_artifact_id=_artifact("retrieval"),
        document_id="document",
        source_id="source",
        section_path=("article",),
        locator=ImmutableEvidenceLocator(
            artifact_id=_artifact("locator"),
            source_artifact_id=_artifact("source"),
            source_uri="https://example.test/source",
            source_content_sha256=_sha("source-content"),
            scheme="unicode-code-point",
            selectors=(("char_start", 0), ("char_end", len(text))),
        ),
        exact_text=text,
        exact_text_sha256=_sha(text),
        rank=1,
        relevance_score=1.0,
        claim_keys=("primary",),
    )
    packet = EvidencePacketBuilder(
        EvidencePacketPolicy(
            token_budget=100,
            citation_budget=1,
            claim_budget=1,
            max_per_source=1,
            max_per_section=1,
        )
    ).build(
        question_artifact_id=_artifact("question"),
        scope_artifact_id=_artifact("scope"),
        retrieval_trace_artifact_ids=(_artifact("trace"),),
        candidates=(evidence,),
    )
    return packet, evidence


def _candidate(citation_id: str, **changes: object) -> dict[str, object]:
    value: dict[str, object] = {
        "schema_version": "bijux.canon.reason.provider_synthesis_candidate.v1",
        "outcome": "answered",
        "answer": "The source reports one scoped observation.",
        "claims": [
            {
                "statement": "The study reports a scoped observation.",
                "citation_evidence_artifact_ids": [citation_id],
                "polarity": "supports",
                "qualifier": "within the admitted study",
                "scope": "the source study",
            }
        ],
        "limitations": ["No generalization beyond the source."],
        "conflicts": [],
        "assumptions": [],
    }
    value.update(changes)
    return value


def _envelope(
    content: object,
    *,
    request_id: str = "request-1",
    input_tokens: int = 100,
    output_tokens: int = 40,
) -> bytes:
    return json.dumps(
        {
            "id": request_id,
            "choices": [
                {
                    "finish_reason": "stop",
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {
                "prompt_tokens": input_tokens,
                "completion_tokens": output_tokens,
            },
        }
    ).encode()


class QueueTransport:
    def __init__(self, responses: list[JsonHttpResponse | Exception]) -> None:
        self.responses = responses
        self.requests: list[tuple[str, dict[str, str], dict[str, object]]] = []

    def post_json(
        self,
        url: str,
        *,
        headers: dict[str, str],
        body: bytes,
        timeout_seconds: float,
        max_response_bytes: int,
    ) -> JsonHttpResponse:
        del timeout_seconds, max_response_bytes
        self.requests.append((url, headers, json.loads(body)))
        response = self.responses.pop(0)
        if isinstance(response, Exception):
            raise response
        return response


def _provider(
    transport: QueueTransport,
    *,
    credential=lambda: "test-secret",
    policy: StructuredProviderPolicy | None = None,
) -> OpenAICompatibleStructuredSynthesizer:
    return OpenAICompatibleStructuredSynthesizer(
        StructuredProviderConfiguration(
            base_url="http://127.0.0.1:8765",
            model="test-model",
            provider="test-compatible",
        ),
        credential_resolver=credential,
        transport=transport,
        policy=policy,
    )


def _response(body: bytes, status: int = 200, duration: int = 7) -> JsonHttpResponse:
    return JsonHttpResponse(status, body, duration, "request-id")


def test_valid_candidate_records_secret_safe_usage_latency_and_schema() -> None:
    packet, evidence = _packet()
    candidate = _candidate(evidence.artifact_id)
    transport = QueueTransport([_response(_envelope(json.dumps(candidate)))])

    result = _provider(transport).synthesize(
        question="What does the study report?", evidence_packet=packet
    )

    assert result.candidate.outcome is CandidateOutcome.answered
    assert result.prompt_artifact_id == prompt_artifact_id()
    assert result.response_schema_sha256 == response_schema_sha256()
    assert result.attempts[0].status is ProviderAttemptStatus.accepted
    assert result.attempts[0].input_tokens == 100
    assert result.attempts[0].output_tokens == 40
    assert result.attempts[0].duration_ms == 7
    assert "test-secret" not in result.model_dump_json()
    request_body = transport.requests[0][2]
    response_format = request_body["response_format"]
    assert isinstance(response_format, dict)
    assert response_format["type"] == "json_schema"
    assert response_format["json_schema"]["strict"] is True


def test_credentials_are_resolved_only_when_synthesis_runs() -> None:
    calls = 0

    def credential() -> str:
        nonlocal calls
        calls += 1
        return "test-secret"

    transport = QueueTransport(
        [
            StructuredProviderError(
                StructuredProviderErrorCode.transport_failed,
                "simulated transport failure",
            )
        ]
    )
    provider = _provider(
        transport,
        credential=credential,
        policy=StructuredProviderPolicy(max_attempts=1, max_repairs=0),
    )
    assert calls == 0

    with pytest.raises(StructuredProviderError) as caught:
        provider.synthesize(question="Question?", evidence_packet=_packet()[0])

    assert calls == 1
    assert caught.value.code is StructuredProviderErrorCode.attempts_exhausted


def test_invalid_candidate_is_repaired_once() -> None:
    packet, evidence = _packet()
    valid = _candidate(evidence.artifact_id)
    transport = QueueTransport(
        [
            _response(_envelope("not-json"), duration=3),
            _response(_envelope(json.dumps(valid)), duration=4),
        ]
    )

    result = _provider(transport).synthesize(
        question="Question?", evidence_packet=packet
    )

    assert tuple(item.kind for item in result.attempts) == (
        ProviderAttemptKind.initial,
        ProviderAttemptKind.repair,
    )
    assert result.attempts[0].validation_error_codes == ("candidate_schema_invalid",)
    assert len(transport.requests[1][2]["messages"]) == 4


def test_unknown_citation_is_repaired_before_acceptance() -> None:
    packet, evidence = _packet()
    invalid = _candidate(_artifact("outside-packet"))
    valid = _candidate(evidence.artifact_id)
    transport = QueueTransport(
        [
            _response(_envelope(json.dumps(invalid))),
            _response(_envelope(json.dumps(valid))),
        ]
    )

    result = _provider(transport).synthesize(
        question="Question?", evidence_packet=packet
    )

    assert result.attempts[0].validation_error_codes == ("citation_outside_packet",)
    assert result.candidate.claims[0].citation_evidence_artifact_ids == (
        evidence.artifact_id,
    )


def test_retryable_status_is_retried_without_using_repair_budget() -> None:
    packet, evidence = _packet()
    transport = QueueTransport(
        [
            _response(b'{"error":"rate limited"}', status=429),
            _response(_envelope(json.dumps(_candidate(evidence.artifact_id)))),
        ]
    )

    result = _provider(transport).synthesize(
        question="Question?", evidence_packet=packet
    )

    assert tuple(item.kind for item in result.attempts) == (
        ProviderAttemptKind.initial,
        ProviderAttemptKind.retry,
    )
    assert result.attempts[0].status is ProviderAttemptStatus.retryable_error


def test_nonretryable_provider_rejection_fails_immediately() -> None:
    transport = QueueTransport([_response(b'{"error":"bad request"}', status=400)])

    with pytest.raises(StructuredProviderError) as caught:
        _provider(transport).synthesize(
            question="Question?", evidence_packet=_packet()[0]
        )

    assert caught.value.code is StructuredProviderErrorCode.provider_rejected
    assert len(caught.value.attempts) == 1
    assert len(transport.requests) == 1


def test_bounded_invalid_responses_end_with_typed_attempt_history() -> None:
    transport = QueueTransport(
        [_response(_envelope("bad")), _response(_envelope("still bad"))]
    )
    policy = StructuredProviderPolicy(max_attempts=2, max_repairs=1)

    with pytest.raises(StructuredProviderError) as caught:
        _provider(transport, policy=policy).synthesize(
            question="Question?", evidence_packet=_packet()[0]
        )

    assert caught.value.code is StructuredProviderErrorCode.attempts_exhausted
    assert len(caught.value.attempts) == 2
    assert all(
        item.status is ProviderAttemptStatus.invalid_candidate
        for item in caught.value.attempts
    )


def test_explicit_provider_refusal_is_not_repaired() -> None:
    refusal = json.dumps(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "refusal": "I cannot answer this request.",
                    }
                }
            ]
        }
    ).encode()
    transport = QueueTransport([_response(refusal)])

    result = _provider(transport).synthesize(
        question="Question?", evidence_packet=_packet()[0]
    )

    assert result.candidate.outcome is CandidateOutcome.refused
    assert result.candidate.claims == ()
    assert result.attempts[0].status is ProviderAttemptStatus.refused
    assert len(transport.requests) == 1


def test_missing_selected_provider_credential_fails_before_transport() -> None:
    transport = QueueTransport([])

    with pytest.raises(StructuredProviderError) as caught:
        _provider(transport, credential=lambda: " ").synthesize(
            question="Question?", evidence_packet=_packet()[0]
        )

    assert caught.value.code is StructuredProviderErrorCode.credential_missing
    assert transport.requests == []


def test_result_is_content_addressed_and_restart_safe() -> None:
    packet, evidence = _packet()
    response = _response(_envelope(json.dumps(_candidate(evidence.artifact_id))))
    result = _provider(QueueTransport([response])).synthesize(
        question="Question?", evidence_packet=packet
    )

    restarted = StructuredProviderSynthesis.model_validate_json(
        result.model_dump_json()
    )
    assert restarted == result

    drifted = result.model_dump(mode="json")
    drifted["artifact_id"] = _artifact("other-result")
    with pytest.raises(ValidationError, match="identity"):
        StructuredProviderSynthesis.model_validate(drifted)


@pytest.mark.parametrize(
    "url",
    [
        "http://provider.example/v1",
        "https://user:secret@provider.example",
        "https://provider.example?secret=value",
    ],
)
def test_provider_configuration_rejects_unsafe_urls(url: str) -> None:
    with pytest.raises(ValueError, match="URL"):
        StructuredProviderConfiguration(base_url=url, model="model")


class _Server(ThreadingHTTPServer):
    responses: list[tuple[int, bytes]]
    requests: list[dict[str, object]]
    authorization: list[str | None]


class _Handler(BaseHTTPRequestHandler):
    server: _Server

    def do_POST(self) -> None:  # noqa: N802
        length = int(self.headers["content-length"])
        self.server.requests.append(json.loads(self.rfile.read(length)))
        self.server.authorization.append(self.headers.get("authorization"))
        status, body = self.server.responses.pop(0)
        self.send_response(status)
        self.send_header("content-type", "application/json")
        self.send_header("x-request-id", "mock-server-request")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        del format, args


@contextmanager
def _mock_server(response: bytes) -> Iterator[_Server]:
    server = _Server(("127.0.0.1", 0), _Handler)
    server.responses = [(200, response)]
    server.requests = []
    server.authorization = []
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_standard_transport_against_deterministic_local_mock_server() -> None:
    packet, evidence = _packet()
    response = _envelope(json.dumps(_candidate(evidence.artifact_id)))
    with _mock_server(response) as server:
        provider = OpenAICompatibleStructuredSynthesizer(
            StructuredProviderConfiguration(
                base_url=f"http://127.0.0.1:{server.server_port}",
                model="mock-server-model",
            ),
            credential_resolver=lambda: "server-secret",
        )
        result = provider.synthesize(
            question="What does the source report?", evidence_packet=packet
        )

    assert result.candidate.outcome is CandidateOutcome.answered
    assert server.authorization == ["Bearer server-secret"]
    assert server.requests[0]["response_format"]["json_schema"]["strict"] is True
    assert "server-secret" not in result.model_dump_json()
