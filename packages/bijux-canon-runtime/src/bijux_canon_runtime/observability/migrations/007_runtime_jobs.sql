-- INTERNAL — NOT A PUBLIC EXTENSION POINT
-- SPDX-License-Identifier: Apache-2.0
-- Copyright © 2026 Bijan Mousavi

CREATE TABLE IF NOT EXISTS runtime_jobs (
    job_id TEXT PRIMARY KEY,
    kind TEXT NOT NULL CHECK (kind IN ('run', 'replay')),
    idempotency_key TEXT NOT NULL UNIQUE,
    request_sha256 TEXT NOT NULL,
    request_artifact_id TEXT NOT NULL,
    status TEXT NOT NULL CHECK (
        status IN (
            'queued', 'running', 'succeeded', 'failed',
            'cancelled', 'timed_out'
        )
    ),
    cancel_requested BOOLEAN NOT NULL,
    attempt_count INTEGER NOT NULL CHECK (attempt_count >= 0),
    submitted_at TEXT NOT NULL,
    started_at TEXT,
    finished_at TEXT,
    deadline_at TEXT,
    timeout_seconds DOUBLE,
    result_artifact_id TEXT,
    error_type TEXT,
    error_message TEXT,
    FOREIGN KEY (request_artifact_id) REFERENCES artifact_payloads (artifact_id),
    FOREIGN KEY (result_artifact_id) REFERENCES artifact_payloads (artifact_id)
);

CREATE INDEX IF NOT EXISTS runtime_jobs_status_idx
    ON runtime_jobs (status, submitted_at, job_id);
