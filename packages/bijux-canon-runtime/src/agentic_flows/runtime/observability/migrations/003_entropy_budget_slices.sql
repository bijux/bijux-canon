-- INTERNAL — NOT A PUBLIC EXTENSION POINT
-- SPDX-License-Identifier: Apache-2.0
-- Copyright © 2025 Bijan Mousavi

CREATE TABLE IF NOT EXISTS entropy_budget_slices (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('seeded_rng', 'external_oracle', 'human_input', 'data')),
    min_magnitude TEXT NOT NULL CHECK (min_magnitude IN ('low', 'medium', 'high')),
    max_magnitude TEXT NOT NULL CHECK (max_magnitude IN ('low', 'medium', 'high')),
    exhaustion_action TEXT CHECK (exhaustion_action IN ('halt', 'degrade', 'mark_non_certifiable')),
    PRIMARY KEY (tenant_id, run_id, source),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);
