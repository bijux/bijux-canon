ALTER TABLE runs ADD COLUMN replay_mode TEXT DEFAULT 'strict';
ALTER TABLE runs ADD COLUMN allowed_variance_class TEXT;
ALTER TABLE runs ADD COLUMN entropy_exhausted BOOLEAN DEFAULT FALSE;
ALTER TABLE runs ADD COLUMN entropy_exhaustion_action TEXT;
ALTER TABLE runs ADD COLUMN non_certifiable BOOLEAN DEFAULT FALSE;

ALTER TABLE steps ADD COLUMN declared_entropy_min_magnitude TEXT;
ALTER TABLE steps ADD COLUMN declared_entropy_max_magnitude TEXT;
ALTER TABLE steps ADD COLUMN declared_entropy_exhaustion_action TEXT;
ALTER TABLE steps ADD COLUMN allowed_variance_class TEXT;

CREATE TABLE IF NOT EXISTS entropy_budget (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    min_magnitude TEXT NOT NULL,
    max_magnitude TEXT NOT NULL,
    exhaustion_action TEXT NOT NULL,
    allowed_variance_class TEXT,
    PRIMARY KEY (tenant_id, run_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS nondeterminism_intents (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_index INTEGER,
    intent_index INTEGER NOT NULL,
    intent_source TEXT NOT NULL,
    min_entropy_magnitude TEXT NOT NULL,
    max_entropy_magnitude TEXT NOT NULL,
    justification TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, step_index, intent_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);
