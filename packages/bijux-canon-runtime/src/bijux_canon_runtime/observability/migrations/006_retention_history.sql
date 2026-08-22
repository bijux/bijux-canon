-- INTERNAL — NOT A PUBLIC EXTENSION POINT
-- SPDX-License-Identifier: Apache-2.0
-- Copyright © 2026 Bijan Mousavi

CREATE TABLE IF NOT EXISTS artifact_holds (
    hold_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    reason TEXT NOT NULL,
    created_at TEXT NOT NULL,
    released_at TEXT,
    PRIMARY KEY (hold_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS garbage_collection_plans (
    plan_id TEXT PRIMARY KEY,
    plan_sha256 TEXT NOT NULL,
    reachability_sha256 TEXT NOT NULL,
    policy_json TEXT NOT NULL,
    status TEXT NOT NULL CHECK (status IN ('planned', 'applied', 'verified', 'rolled_back')),
    created_at TEXT NOT NULL,
    applied_at TEXT,
    verified_at TEXT,
    rolled_back_at TEXT,
    backup_root TEXT
);

CREATE TABLE IF NOT EXISTS garbage_collection_candidates (
    plan_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    classification TEXT NOT NULL CHECK (classification IN ('orphan', 'superseded')),
    disposition TEXT NOT NULL CHECK (disposition IN ('eligible', 'held')),
    reason TEXT NOT NULL,
    PRIMARY KEY (plan_id, artifact_id)
);

CREATE INDEX IF NOT EXISTS artifact_holds_active_idx
    ON artifact_holds (artifact_id, released_at);
CREATE INDEX IF NOT EXISTS garbage_collection_plans_status_idx
    ON garbage_collection_plans (status);
