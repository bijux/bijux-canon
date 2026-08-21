# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi
"""Inspectable secret-safe immutable RAG execution persistence tests."""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from bijux_canon_reason.grounding import (
    ContentAddressedRagExecutionStore,
    RagExecutionBundle,
    RagExecutionMode,
    RagExecutionPersistenceError,
    RagExecutionPersistenceErrorCode,
    RagExecutionRecorder,
    RagExecutionStageKind,
    create_rag_execution_budget,
    create_rag_execution_failure,
)


def _artifact(value: str) -> str:
    return "sha256:" + hashlib.sha256(value.encode()).hexdigest()


def _stage_payloads():
    return tuple(
        (kind, _artifact(kind.value), {"kind": kind.value, "value": "inspectable"})
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


def _budget(*, evidence_tokens_observed: int = 40):
    return create_rag_execution_budget(
        evidence_token_limit=100,
        evidence_tokens_observed=evidence_tokens_observed,
        citation_limit=4,
        citations_observed=2,
        provider_attempt_limit=3,
        provider_attempts_observed=1,
        provider_input_tokens=20,
        provider_output_tokens=10,
    )


def _bundle(*, failures=(), known_secrets=()):
    return RagExecutionRecorder().record(
        mode=RagExecutionMode.structured_provider,
        question="What do the admitted sources report?",
        stage_payloads=_stage_payloads(),
        budget=_budget(),
        failures=failures,
        final_answer="A verified answer with exact citations.",
        known_secrets=known_secrets,
    )


def test_complete_bundle_persists_and_replays_exactly(tmp_path: Path) -> None:
    failure = create_rag_execution_failure(
        stage=RagExecutionStageKind.synthesis_output,
        code="bounded_repair",
        message="Provider returned invalid candidate JSON.",
    )
    bundle = _bundle(failures=(failure,), known_secrets=("not-present-secret",))
    store = ContentAddressedRagExecutionStore(tmp_path / "rag-store")

    manifest_path = store.persist(bundle)
    restarted = store.load(bundle.manifest.artifact_id)

    assert manifest_path.is_file()
    assert restarted == bundle
    assert restarted.manifest.secret_redaction_count == 1
    assert {stage.kind for stage in restarted.stages} == set(RagExecutionStageKind)


def test_failure_retains_digest_but_not_raw_diagnostic() -> None:
    message = "Provider diagnostic that may contain operational detail."
    failure = create_rag_execution_failure(
        stage=RagExecutionStageKind.synthesis_output,
        code="provider_failure",
        message=message,
    )
    bundle = _bundle(failures=(failure,))

    assert message not in bundle.model_dump_json()
    assert hashlib.sha256(message.encode()).hexdigest() in bundle.model_dump_json()


def test_known_secret_value_is_rejected_before_persistence() -> None:
    secret = "credential-material"
    payloads = list(_stage_payloads())
    payloads[0] = (payloads[0][0], payloads[0][1], {"template": secret})

    with pytest.raises(RagExecutionPersistenceError) as caught:
        RagExecutionRecorder().record(
            mode=RagExecutionMode.structured_provider,
            question="Question?",
            stage_payloads=tuple(payloads),
            budget=_budget(),
            failures=(),
            final_answer="Abstained.",
            known_secrets=(secret,),
        )

    assert caught.value.code is RagExecutionPersistenceErrorCode.known_secret_present


def test_sensitive_payload_key_is_rejected_before_persistence() -> None:
    payloads = list(_stage_payloads())
    payloads[0] = (payloads[0][0], payloads[0][1], {"api_key": "redacted"})

    with pytest.raises(RagExecutionPersistenceError) as caught:
        RagExecutionRecorder().record(
            mode=RagExecutionMode.structured_provider,
            question="Question?",
            stage_payloads=tuple(payloads),
            budget=_budget(),
            failures=(),
            final_answer="Abstained.",
        )

    assert caught.value.code is RagExecutionPersistenceErrorCode.sensitive_payload


def test_missing_required_stage_is_rejected() -> None:
    with pytest.raises(RagExecutionPersistenceError) as caught:
        RagExecutionRecorder().record(
            mode=RagExecutionMode.credential_free,
            question="Question?",
            stage_payloads=_stage_payloads()[:-1],
            budget=_budget(),
            failures=(),
            final_answer="Answer.",
        )

    assert caught.value.code is RagExecutionPersistenceErrorCode.required_stage_missing


def test_duplicate_stage_is_rejected() -> None:
    payloads = _stage_payloads()

    with pytest.raises(RagExecutionPersistenceError) as caught:
        RagExecutionRecorder().record(
            mode=RagExecutionMode.credential_free,
            question="Question?",
            stage_payloads=(*payloads, payloads[0]),
            budget=_budget(),
            failures=(),
            final_answer="Answer.",
        )

    assert caught.value.code is RagExecutionPersistenceErrorCode.duplicate_stage


def test_observed_budget_overflow_is_rejected() -> None:
    with pytest.raises(ValidationError, match="exceed"):
        _budget(evidence_tokens_observed=101)


def test_store_detects_existing_object_collision(tmp_path: Path) -> None:
    bundle = _bundle()
    store_root = tmp_path / "rag-store"
    store = ContentAddressedRagExecutionStore(store_root)
    store.persist(bundle)
    stage = bundle.stages[0]
    object_path = (
        store_root / "objects" / f"{stage.artifact_id.removeprefix('sha256:')}.json"
    )
    object_path.write_text("conflicting bytes")

    with pytest.raises(RagExecutionPersistenceError) as caught:
        store.persist(bundle)

    assert caught.value.code is RagExecutionPersistenceErrorCode.object_collision


def test_store_detects_corrupt_object_during_replay(tmp_path: Path) -> None:
    bundle = _bundle()
    store_root = tmp_path / "rag-store"
    store = ContentAddressedRagExecutionStore(store_root)
    store.persist(bundle)
    stage = bundle.stages[0]
    object_path = (
        store_root / "objects" / f"{stage.artifact_id.removeprefix('sha256:')}.json"
    )
    object_path.write_text("{}")

    with pytest.raises(RagExecutionPersistenceError) as caught:
        store.load(bundle.manifest.artifact_id)

    assert caught.value.code is RagExecutionPersistenceErrorCode.object_corrupt


def test_bundle_restart_validation_rejects_manifest_stage_drift() -> None:
    bundle = _bundle()
    drifted = bundle.model_dump(mode="json")
    drifted["manifest"]["stage_artifact_ids"] = []

    with pytest.raises(ValidationError):
        RagExecutionBundle.model_validate(drifted)
