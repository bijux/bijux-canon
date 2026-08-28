-- INTERNAL — NOT A PUBLIC EXTENSION POINT
-- SPDX-License-Identifier: Apache-2.0
-- Copyright © 2026 Bijan Mousavi

CREATE TABLE IF NOT EXISTS artifact_payloads (
    artifact_id TEXT PRIMARY KEY,
    schema_id TEXT NOT NULL,
    media_type TEXT NOT NULL,
    size_bytes BIGINT NOT NULL CHECK (size_bytes >= 0),
    payload_sha256 TEXT NOT NULL,
    producer TEXT NOT NULL,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS artifact_payload_dependencies (
    artifact_id TEXT NOT NULL,
    dependency_artifact_id TEXT NOT NULL,
    PRIMARY KEY (artifact_id, dependency_artifact_id),
    FOREIGN KEY (artifact_id) REFERENCES artifact_payloads (artifact_id),
    FOREIGN KEY (dependency_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_revisions (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    state_hash TEXT NOT NULL,
    payload_artifact_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, revision),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (payload_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_dags (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    dag_version INTEGER NOT NULL CHECK (dag_version >= 1),
    dag_hash TEXT NOT NULL,
    payload_artifact_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, dag_version),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (payload_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_attempts (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    attempt_id TEXT NOT NULL,
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    attempt_number INTEGER NOT NULL CHECK (attempt_number >= 1),
    status TEXT NOT NULL CHECK (status IN ('running', 'succeeded', 'failed', 'cancelled')),
    started_at TEXT NOT NULL,
    finished_at TEXT,
    failure_artifact_id TEXT,
    PRIMARY KEY (tenant_id, run_id, attempt_id),
    UNIQUE (tenant_id, run_id, step_index, attempt_number),
    FOREIGN KEY (tenant_id, run_id, step_index)
        REFERENCES steps (tenant_id, run_id, step_index),
    FOREIGN KEY (failure_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS artifact_references (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    logical_artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    target_artifact_id TEXT NOT NULL,
    reference_state TEXT NOT NULL CHECK (reference_state IN ('active', 'superseded')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, logical_artifact_id, revision),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (target_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_policies (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    policy_kind TEXT NOT NULL,
    policy_id TEXT NOT NULL,
    payload_artifact_id TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, policy_kind, policy_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (payload_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_checks (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    check_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('passed', 'failed')),
    evidence_artifact_id TEXT NOT NULL,
    checked_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, check_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (evidence_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE TABLE IF NOT EXISTS run_publications (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    publication_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    publication_state TEXT NOT NULL CHECK (publication_state IN ('draft', 'admitted', 'revoked')),
    selected_attempt_id TEXT NOT NULL,
    manifest_artifact_id TEXT NOT NULL,
    receipt_artifact_id TEXT NOT NULL,
    stable_citation TEXT NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, publication_id, revision),
    FOREIGN KEY (tenant_id, run_id, selected_attempt_id)
        REFERENCES run_attempts (tenant_id, run_id, attempt_id),
    FOREIGN KEY (manifest_artifact_id) REFERENCES artifact_payloads (artifact_id),
    FOREIGN KEY (receipt_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE INDEX IF NOT EXISTS artifact_references_target_idx
    ON artifact_references (target_artifact_id);
CREATE INDEX IF NOT EXISTS run_attempts_step_idx
    ON run_attempts (tenant_id, run_id, step_index, attempt_number);
