-- INTERNAL — NOT A PUBLIC EXTENSION POINT
-- SPDX-License-Identifier: Apache-2.0
-- Copyright © 2026 Bijan Mousavi

CREATE TABLE IF NOT EXISTS publication_transactions (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    intent_hash TEXT NOT NULL,
    intent_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('prepared', 'committed', 'aborted')),
    failure_reason TEXT,
    created_at TEXT NOT NULL,
    completed_at TEXT,
    PRIMARY KEY (tenant_id, run_id, transaction_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS publication_transaction_artifacts (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    transaction_id TEXT NOT NULL,
    logical_artifact_id TEXT NOT NULL,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    target_artifact_id TEXT NOT NULL,
    PRIMARY KEY (
        tenant_id, run_id, transaction_id, logical_artifact_id, revision
    ),
    FOREIGN KEY (target_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE INDEX IF NOT EXISTS publication_transactions_status_idx
    ON publication_transactions (tenant_id, run_id, status);
