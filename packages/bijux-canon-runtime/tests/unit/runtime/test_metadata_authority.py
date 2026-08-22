from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from bijux_canon_runtime.model.artifact import AddressedArtifact
from bijux_canon_runtime.model.execution.run_mode import RunMode
from bijux_canon_runtime.observability.storage.execution_store import (
    DuckDBExecutionWriteStore,
)
from bijux_canon_runtime.ontology.ids import ArtifactID, RunID, TenantID
from bijux_canon_runtime.runtime.persistence import (
    ArtifactReferenceRecord,
    AttemptStatus,
    CheckStatus,
    DuckDBMetadataAuthority,
    MetadataIntegrityError,
    PublicationState,
    ReferenceState,
    RunAttemptRecord,
    RunCheckRecord,
    RunDagRecord,
    RunPolicyRecord,
    RunPublicationRecord,
    RunRevisionRecord,
)

_NOW = "2026-08-22T00:00:00+00:00"


def _seed_run(db_path: Path, resolved_flow) -> tuple[TenantID, RunID]:
    store = DuckDBExecutionWriteStore(db_path)
    run_id = store.save_run(
        trace=None,
        plan=resolved_flow.plan,
        mode=RunMode.DRY_RUN,
    )
    store._store.close()
    return resolved_flow.manifest.tenant_id, run_id


def test_metadata_authority_persists_complete_versioned_run_graph(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path = tmp_path / "runtime.duckdb"
    tenant_id, run_id = _seed_run(db_path, resolved_flow)
    payloads = {
        name: AddressedArtifact.from_json(
            {"kind": name, "run_id": str(run_id)},
            schema_id=f"bijux.runtime.{name}.v1",
            producer=f"bijux-canon-runtime:{name}",
        )
        for name in ("state", "dag", "policy", "check", "manifest", "receipt")
    }

    with DuckDBMetadataAuthority(db_path) as authority:
        for artifact in payloads.values():
            authority.register_payload(artifact.descriptor, created_at=_NOW)
        authority.record_run_revision(
            RunRevisionRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                revision=0,
                state_hash=str(payloads["state"].descriptor.payload_sha256),
                payload_artifact_id=payloads["state"].descriptor.artifact_id,
                created_at=_NOW,
            )
        )
        authority.record_dag(
            RunDagRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                dag_version=1,
                dag_hash=str(payloads["dag"].descriptor.payload_sha256),
                payload_artifact_id=payloads["dag"].descriptor.artifact_id,
                created_at=_NOW,
            )
        )
        authority.record_attempt(
            RunAttemptRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                attempt_id="attempt-1",
                step_index=0,
                attempt_number=1,
                status=AttemptStatus.SUCCEEDED,
                started_at=_NOW,
                finished_at=_NOW,
            )
        )
        authority.record_reference(
            ArtifactReferenceRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                logical_artifact_id="run-current",
                revision=0,
                target_artifact_id=payloads["state"].descriptor.artifact_id,
                reference_state=ReferenceState.ACTIVE,
                created_at=_NOW,
            )
        )
        authority.record_policy(
            RunPolicyRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                policy_kind="tool-policy",
                policy_id="policy-1",
                payload_artifact_id=payloads["policy"].descriptor.artifact_id,
                created_at=_NOW,
            )
        )
        authority.record_check(
            RunCheckRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                check_id="grounding",
                status=CheckStatus.PASSED,
                evidence_artifact_id=payloads["check"].descriptor.artifact_id,
                checked_at=_NOW,
            )
        )
        authority.record_publication(
            RunPublicationRecord(
                tenant_id=tenant_id,
                run_id=run_id,
                publication_id="ancient-dna-run",
                revision=0,
                publication_state=PublicationState.ADMITTED,
                selected_attempt_id="attempt-1",
                manifest_artifact_id=payloads["manifest"].descriptor.artifact_id,
                receipt_artifact_id=payloads["receipt"].descriptor.artifact_id,
                stable_citation="bijux:run:ancient-dna-run:0",
                created_at=_NOW,
            )
        )

    with DuckDBMetadataAuthority(db_path) as restarted:
        assert restarted.counts(tenant_id=tenant_id, run_id=run_id) == {
            "run_revisions": 1,
            "run_dags": 1,
            "run_attempts": 1,
            "artifact_references": 1,
            "run_policies": 1,
            "run_checks": 1,
            "run_publications": 1,
        }


def test_metadata_authority_rejects_unknown_relationships(
    tmp_path: Path,
    resolved_flow,
) -> None:
    db_path = tmp_path / "runtime.duckdb"
    tenant_id, run_id = _seed_run(db_path, resolved_flow)
    missing = ArtifactID("sha256:" + "a" * 64)
    with DuckDBMetadataAuthority(db_path) as authority:
        with pytest.raises(MetadataIntegrityError, match="unknown or invalid"):
            authority.record_dag(
                RunDagRecord(
                    tenant_id=tenant_id,
                    run_id=run_id,
                    dag_version=1,
                    dag_hash="hash",
                    payload_artifact_id=missing,
                    created_at=_NOW,
                )
            )
        with pytest.raises(MetadataIntegrityError, match="unknown or invalid"):
            authority.record_check(
                RunCheckRecord(
                    tenant_id=TenantID("unknown-tenant"),
                    run_id=RunID("unknown-run"),
                    check_id="check",
                    status=CheckStatus.FAILED,
                    evidence_artifact_id=missing,
                    checked_at=_NOW,
                )
            )


def test_payload_metadata_is_idempotent_and_conflicts_fail_closed(
    tmp_path: Path,
) -> None:
    artifact = AddressedArtifact.from_json(
        {"trace": ["start", "finish"]},
        schema_id="bijux.runtime.trace.v1",
        producer="bijux-canon-runtime:trace",
    )
    with DuckDBMetadataAuthority(tmp_path / "runtime.duckdb") as authority:
        authority.register_payload(artifact.descriptor, created_at=_NOW)
        authority.register_payload(artifact.descriptor, created_at=_NOW)
        conflicting = replace(
            artifact.descriptor,
            producer="bijux-canon-runtime:conflicting-producer",
        )
        with pytest.raises(MetadataIntegrityError, match="conflicts"):
            authority.register_payload(conflicting, created_at=_NOW)


def test_failed_attempt_requires_immutable_failure_payload(tmp_path: Path) -> None:
    with (
        DuckDBMetadataAuthority(tmp_path / "runtime.duckdb") as authority,
        pytest.raises(MetadataIntegrityError, match="failure artifact"),
    ):
        authority.record_attempt(
            RunAttemptRecord(
                tenant_id=TenantID("tenant-a"),
                run_id=RunID("run-a"),
                attempt_id="attempt-a",
                step_index=0,
                attempt_number=1,
                status=AttemptStatus.FAILED,
                started_at=_NOW,
                finished_at=_NOW,
            )
        )
