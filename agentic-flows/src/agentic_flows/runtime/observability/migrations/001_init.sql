-- 001: Canonical execution store schema
CREATE TABLE IF NOT EXISTS schema_contract (
    schema_version INTEGER PRIMARY KEY,
    schema_hash TEXT NOT NULL,
    applied_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_state_transitions (
    from_state TEXT NOT NULL CHECK (from_state IN ('experimental', 'frozen', 'deprecated')),
    to_state TEXT NOT NULL CHECK (to_state IN ('experimental', 'frozen', 'deprecated')),
    PRIMARY KEY (from_state, to_state)
);

INSERT OR IGNORE INTO dataset_state_transitions (from_state, to_state) VALUES
    ('experimental', 'experimental'),
    ('experimental', 'frozen'),
    ('experimental', 'deprecated'),
    ('frozen', 'frozen'),
    ('frozen', 'deprecated'),
    ('deprecated', 'deprecated');

CREATE TABLE IF NOT EXISTS datasets (
    tenant_id TEXT NOT NULL,
    dataset_id TEXT NOT NULL,
    version TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('experimental', 'frozen', 'deprecated')),
    previous_state TEXT CHECK (previous_state IN ('experimental', 'frozen', 'deprecated')),
    CHECK (
        previous_state IS NULL
        OR (previous_state = 'experimental' AND state IN ('experimental', 'frozen', 'deprecated'))
        OR (previous_state = 'frozen' AND state IN ('frozen', 'deprecated'))
        OR (previous_state = 'deprecated' AND state = 'deprecated')
    ),
    fingerprint TEXT NOT NULL,
    storage_uri TEXT NOT NULL,
    PRIMARY KEY (tenant_id, dataset_id, version),
    FOREIGN KEY (previous_state, state)
        REFERENCES dataset_state_transitions (from_state, to_state)
);

CREATE TABLE IF NOT EXISTS runs (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    flow_id TEXT NOT NULL,
    flow_state TEXT NOT NULL CHECK (flow_state IN ('draft', 'validated', 'frozen', 'deprecated')),
    determinism_level TEXT NOT NULL CHECK (determinism_level IN ('strict', 'bounded', 'probabilistic', 'unconstrained')),
    replay_acceptability TEXT NOT NULL CHECK (replay_acceptability IN ('exact_match', 'invariant_preserving', 'statistically_bounded')),
    dataset_id TEXT NOT NULL,
    dataset_version TEXT NOT NULL,
    dataset_state TEXT NOT NULL CHECK (dataset_state IN ('experimental', 'frozen', 'deprecated')),
    dataset_hash TEXT NOT NULL,
    dataset_storage_uri TEXT NOT NULL,
    allow_deprecated_datasets BOOLEAN NOT NULL,
    replay_envelope_min_claim_overlap DOUBLE NOT NULL CHECK (replay_envelope_min_claim_overlap >= 0 AND replay_envelope_min_claim_overlap <= 1),
    replay_envelope_max_contradiction_delta INTEGER NOT NULL CHECK (replay_envelope_max_contradiction_delta >= 0),
    environment_fingerprint TEXT NOT NULL,
    plan_hash TEXT NOT NULL,
    verification_policy_fingerprint TEXT,
    resolver_id TEXT NOT NULL,
    parent_flow_id TEXT,
    contradiction_count INTEGER NOT NULL CHECK (contradiction_count >= 0),
    arbitration_decision TEXT NOT NULL,
    finalized BOOLEAN NOT NULL,
    run_mode TEXT NOT NULL CHECK (run_mode IN ('plan', 'dry-run', 'live', 'observe', 'unsafe')),
    created_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id),
    FOREIGN KEY (tenant_id, dataset_id, dataset_version)
        REFERENCES datasets (tenant_id, dataset_id, version)
);

CREATE TABLE IF NOT EXISTS run_children (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    child_flow_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, child_flow_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS run_checkpoints (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_index INTEGER NOT NULL CHECK (step_index >= -1),
    event_index INTEGER NOT NULL CHECK (event_index >= -1),
    updated_at TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS entropy_budget_sources (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    source TEXT NOT NULL CHECK (source IN ('seeded_rng', 'external_oracle', 'human_input', 'data')),
    PRIMARY KEY (tenant_id, run_id, source),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS entropy_budget_magnitudes (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    magnitude TEXT NOT NULL CHECK (magnitude IN ('low', 'medium', 'high')),
    PRIMARY KEY (tenant_id, run_id, magnitude),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS steps (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    agent_id TEXT NOT NULL,
    step_type TEXT NOT NULL CHECK (step_type IN ('agent', 'retrieval', 'reasoning', 'verification')),
    determinism_level TEXT NOT NULL CHECK (determinism_level IN ('strict', 'bounded', 'probabilistic', 'unconstrained')),
    inputs_fingerprint TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, step_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS step_dependencies (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    step_index INTEGER NOT NULL,
    dependency_agent_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, step_index, dependency_agent_id),
    FOREIGN KEY (tenant_id, run_id, step_index)
        REFERENCES steps (tenant_id, run_id, step_index)
);

CREATE TABLE IF NOT EXISTS events (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    event_index INTEGER NOT NULL CHECK (event_index >= 0),
    step_index INTEGER NOT NULL CHECK (step_index >= 0),
    event_type TEXT NOT NULL CHECK (
        event_type IN (
            'STEP_START',
            'STEP_END',
            'STEP_FAILED',
            'RETRIEVAL_START',
            'RETRIEVAL_END',
            'RETRIEVAL_FAILED',
            'REASONING_START',
            'REASONING_END',
            'REASONING_FAILED',
            'VERIFICATION_START',
            'VERIFICATION_PASS',
            'VERIFICATION_FAIL',
            'VERIFICATION_ESCALATE',
            'VERIFICATION_ARBITRATION',
            'EXECUTION_INTERRUPTED',
            'HUMAN_INTERVENTION',
            'SEMANTIC_VIOLATION',
            'TOOL_CALL_START',
            'TOOL_CALL_END',
            'TOOL_CALL_FAIL'
        )
    ),
    causality_tag TEXT NOT NULL CHECK (
        causality_tag IN ('agent', 'tool', 'dataset', 'environment', 'human')
    ),
    timestamp_utc TEXT NOT NULL,
    payload_hash TEXT NOT NULL,
    agent_id TEXT,
    payload_json TEXT,
    PRIMARY KEY (tenant_id, run_id, event_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS artifacts (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    artifact_type TEXT NOT NULL,
    producer TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    scope TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, artifact_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS artifact_parents (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    artifact_id TEXT NOT NULL,
    parent_artifact_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, artifact_id, parent_artifact_id),
    FOREIGN KEY (tenant_id, run_id, artifact_id)
        REFERENCES artifacts (tenant_id, run_id, artifact_id)
);

CREATE TABLE IF NOT EXISTS evidence (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    entry_index INTEGER NOT NULL CHECK (entry_index >= 0),
    evidence_id TEXT NOT NULL,
    determinism TEXT NOT NULL CHECK (determinism IN ('deterministic', 'sampled', 'external')),
    source_uri TEXT NOT NULL,
    content_hash TEXT NOT NULL,
    score DOUBLE NOT NULL,
    vector_contract_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, entry_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS entropy_usage (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    entry_index INTEGER NOT NULL CHECK (entry_index >= 0),
    source TEXT NOT NULL CHECK (source IN ('seeded_rng', 'external_oracle', 'human_input', 'data')),
    magnitude TEXT NOT NULL CHECK (magnitude IN ('low', 'medium', 'high')),
    description TEXT NOT NULL,
    step_index INTEGER,
    nondeterminism_authorized BOOLEAN NOT NULL,
    nondeterminism_scope_id TEXT NOT NULL,
    nondeterminism_scope_type TEXT NOT NULL CHECK (nondeterminism_scope_type IN ('step', 'flow')),
    PRIMARY KEY (tenant_id, run_id, entry_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id),
    FOREIGN KEY (tenant_id, run_id, source)
        REFERENCES entropy_budget_sources (tenant_id, run_id, source),
    FOREIGN KEY (tenant_id, run_id, magnitude)
        REFERENCES entropy_budget_magnitudes (tenant_id, run_id, magnitude)
);

CREATE TABLE IF NOT EXISTS tool_invocations (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    entry_index INTEGER NOT NULL CHECK (entry_index >= 0),
    tool_id TEXT NOT NULL,
    determinism_level TEXT NOT NULL,
    inputs_fingerprint TEXT NOT NULL,
    outputs_fingerprint TEXT,
    duration DOUBLE NOT NULL,
    outcome TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, entry_index),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE TABLE IF NOT EXISTS claims (
    tenant_id TEXT NOT NULL,
    run_id TEXT NOT NULL,
    claim_id TEXT NOT NULL,
    PRIMARY KEY (tenant_id, run_id, claim_id),
    FOREIGN KEY (tenant_id, run_id) REFERENCES runs (tenant_id, run_id)
);

CREATE INDEX IF NOT EXISTS events_run_step_idx
    ON events (tenant_id, run_id, step_index);
CREATE INDEX IF NOT EXISTS events_run_type_idx
    ON events (tenant_id, run_id, event_type);
CREATE INDEX IF NOT EXISTS events_run_time_idx
    ON events (tenant_id, run_id, timestamp_utc);
