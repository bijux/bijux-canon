# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Cross-package secret handling and provider transport policy tests."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import asdict
import hashlib
import json
from pathlib import Path
from typing import Literal

import pytest

from bijux_canon_index.infra.embeddings.remote import (
    RemoteEmbeddingClient,
    RemoteEmbeddingConfig,
    RemoteEmbeddingTransport,
    RemoteHTTPResponse,
    RemoteTimeouts,
)
from bijux_canon_reason.grounding import (
    ContentAddressedRagExecutionStore,
    RagExecutionMode,
    RagExecutionRecorder,
    RagExecutionStageKind,
    StructuredProviderConfiguration,
    StructuredProviderPolicy,
    create_rag_execution_budget,
)
from bijux_canon_runtime.application.problems import (
    RuntimeProblemCode,
    runtime_problem,
    runtime_problem_fields,
)
from bijux_canon_runtime.application.runtime_configuration import (
    resolve_runtime_configuration,
)

CANARY_SECRET = "bijux-canary-provider-secret-8f70c0c7"


def _artifact(value: str) -> str:
    return f"sha256:{hashlib.sha256(value.encode()).hexdigest()}"


def _stage_payloads() -> tuple[
    tuple[RagExecutionStageKind, str, dict[str, object]], ...
]:
    return tuple(
        (
            kind,
            _artifact(f"domain:{kind.value}"),
            {"kind": kind.value, "state": "inspectable"},
        )
        for kind in (
            RagExecutionStageKind.prompt_template,
            RagExecutionStageKind.evidence_packet,
            RagExecutionStageKind.synthesis_output,
            RagExecutionStageKind.normalized_claims,
            RagExecutionStageKind.citation_links,
            RagExecutionStageKind.verification_report,
            RagExecutionStageKind.admission_decision,
            RagExecutionStageKind.context_representation,
        )
    )


def test_seeded_canary_is_absent_from_config_errors_traces_and_artifacts(
    tmp_path: Path,
) -> None:
    configuration = resolve_runtime_configuration(
        environment={
            "BIJUX_CANON_RUNTIME_PROVIDER_API_KEY_REF": "RESEARCH_PROVIDER_KEY",
            "RESEARCH_PROVIDER_KEY": CANARY_SECRET,
        }
    )
    problem = runtime_problem(
        RuntimeProblemCode.OPERATION_FAILED,
        cause=RuntimeError(
            f"authorization={CANARY_SECRET} at /srv/private/provider.json"
        ),
    )
    budget = create_rag_execution_budget(
        evidence_token_limit=100,
        evidence_tokens_observed=20,
        citation_limit=4,
        citations_observed=2,
        provider_attempt_limit=2,
        provider_attempts_observed=1,
        provider_input_tokens=20,
        provider_output_tokens=10,
    )
    bundle = RagExecutionRecorder().record(
        mode=RagExecutionMode.structured_provider,
        question="What do the admitted sources report?",
        stage_payloads=_stage_payloads(),
        budget=budget,
        failures=(),
        final_answer="The admitted evidence supports a bounded answer.",
        known_secrets=(CANARY_SECRET,),
    )
    store_root = tmp_path / "rag-store"
    store = ContentAddressedRagExecutionStore(store_root)
    store.persist(bundle)
    restarted = store.load(bundle.manifest.artifact_id)

    inspected = json.dumps(
        {
            "configuration": configuration.redacted_record(),
            "problem": runtime_problem_fields(problem),
            "trace": restarted.model_dump(mode="json"),
        },
        sort_keys=True,
    )
    persisted = b"".join(
        path.read_bytes() for path in sorted(store_root.rglob("*")) if path.is_file()
    )

    assert configuration.provider_api_key is not None
    assert (
        configuration.provider_api_key.environment_variable == "RESEARCH_PROVIDER_KEY"
    )
    assert restarted.manifest.secret_redaction_count == 1
    assert "<redacted>" in (problem.cause or "")
    assert "<path>" in (problem.cause or "")
    assert CANARY_SECRET not in inspected
    assert CANARY_SECRET.encode() not in persisted


class _CapturingEmbeddingTransport(RemoteEmbeddingTransport):
    def __init__(self) -> None:
        self.endpoint = ""
        self.headers: Mapping[str, str] = {}
        self.timeouts: RemoteTimeouts | None = None

    def send(
        self,
        *,
        endpoint: str,
        headers: Mapping[str, str],
        body: bytes,
        timeouts: RemoteTimeouts,
        max_response_bytes: int,
    ) -> RemoteHTTPResponse:
        del body, max_response_bytes
        self.endpoint = endpoint
        self.headers = headers
        self.timeouts = timeouts
        return RemoteHTTPResponse(
            status=200,
            headers={"x-request-id": "provider-request-1"},
            body=json.dumps(
                {
                    "data": [{"embedding": [1.0, 0.0], "index": 0}],
                    "model": "locked-embedding-model",
                    "usage": {"prompt_tokens": 4, "total_tokens": 4},
                }
            ).encode(),
        )


def test_provider_secret_crosses_only_the_authorized_header_boundary() -> None:
    events: list[Mapping[str, object]] = []
    transport = _CapturingEmbeddingTransport()
    timeouts = RemoteTimeouts(connect_seconds=2.0, read_seconds=7.0)
    config = RemoteEmbeddingConfig(
        endpoint="https://provider.example/v1/embeddings",
        endpoint_class="public",
        model="locked-embedding-model",
        dimension=2,
        max_attempts=1,
        timeouts=timeouts,
    )
    client = RemoteEmbeddingClient(
        config,
        transport=transport,
        credential_provider=lambda: CANARY_SECRET,
        event_logger=events.append,
    )

    batch = client.embed(("bounded source text",))

    assert transport.endpoint == config.endpoint
    assert transport.headers["Authorization"] == f"Bearer {CANARY_SECRET}"
    assert transport.timeouts == timeouts
    assert batch.provenance.endpoint_class == "public"
    assert CANARY_SECRET not in json.dumps(asdict(batch), sort_keys=True)
    assert CANARY_SECRET not in json.dumps(events, sort_keys=True)


@pytest.mark.parametrize(
    ("base_url", "expected"),
    (
        ("http://provider.example", "unencrypted provider URLs"),
        ("ftp://provider.example", "provider base URL"),
        ("https://user:password@provider.example", "provider base URL"),
        ("https://provider.example?api_key=secret", "provider base URL"),
    ),
)
def test_structured_provider_rejects_unsafe_endpoint_forms(
    base_url: str, expected: str
) -> None:
    with pytest.raises(ValueError, match=expected):
        StructuredProviderConfiguration(base_url=base_url, model="grounded-model")


@pytest.mark.parametrize("endpoint_class", ("public", "private"))
def test_remote_embeddings_require_tls_outside_local_profiles(
    endpoint_class: Literal["public", "private"],
) -> None:
    with pytest.raises(ValueError, match="require HTTPS"):
        RemoteEmbeddingConfig(
            endpoint="http://provider.example/v1/embeddings",
            endpoint_class=endpoint_class,
            model="locked-embedding-model",
            dimension=384,
        )


def test_provider_timeout_policies_are_positive_and_explicit() -> None:
    with pytest.raises(ValueError, match="transport limits"):
        StructuredProviderPolicy(timeout_seconds=0)
    with pytest.raises(ValueError, match="timeouts must be positive"):
        RemoteTimeouts(connect_seconds=0)

    local = StructuredProviderConfiguration(
        base_url="http://127.0.0.1:8080",
        model="local-model",
    )
    remote = StructuredProviderConfiguration(
        base_url="https://provider.example",
        model="remote-model",
    )

    assert local.endpoint == "http://127.0.0.1:8080/v1/chat/completions"
    assert remote.endpoint_origin == "https://provider.example"
