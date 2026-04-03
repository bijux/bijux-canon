# Backward Compatibility Contract (v0.1.x → v0.2.x)

This document defines what **will not change** for v0.1.x users as bijux-vex moves through v0.2.x.
If it is not listed here, it is not guaranteed.

## CLI commands guaranteed unchanged
The following CLI commands (names + core semantics) are frozen from v0.1.x:

- `list-artifacts`
- `capabilities`
- `ingest`
- `materialize`
- `execute`
- `explain`
- `replay`
- `compare`

Notes:

- Flag names and defaults are frozen via snapshot tests; any change requires an explicit test update.
- Output fields are guaranteed as documented below.

## API routes guaranteed unchanged
The following HTTP routes (paths + verbs) are frozen from v0.1.x:

- `GET /capabilities`
- `POST /create`
- `POST /ingest`
- `POST /artifact`
- `POST /execute`
- `POST /explain`
- `POST /replay`

## Output fields guaranteed unchanged (JSON schema)
The following output fields are **stable** across v0.1.x and v0.2.x.
They are contractually frozen unless a new major version is released.

### CLI outputs
- `list-artifacts` → `artifacts`
- `capabilities` → `backend`, `contracts`, `deterministic_query`, `supports_ann`, `replayable`, `metrics`, `max_vector_size`, `isolation_level`, `execution_modes`, `ann_status`, `storage_backends`, `vector_stores`
- `ingest` → `ingested`
- `materialize` → `artifact_id`, `execution_contract`, `execution_contract_status`, `replayable`
- `execute` → `results`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`
- `explain` → `document_id`, `chunk_id`, `vector_id`, `artifact_id`, `metric`, `score`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`
- `replay` → `matches`, `original_fingerprint`, `replay_fingerprint`, `details`, `nondeterministic_sources`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`
- `compare` → `execution_a`, `execution_b`, `overlap_ratio`, `recall_delta`, `rank_instability`, `execution_a_contract`, `execution_b_contract`, `execution_a_contract_status`, `execution_b_contract_status`

### API outputs
- `GET /capabilities` → same fields as CLI `capabilities`
- `POST /create` → `name`, `status`
- `POST /ingest` → `ingested`
- `POST /artifact` → `artifact_id`, `execution_contract`, `execution_contract_status`, `replayable`
- `POST /execute` → `results`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`
- `POST /explain` → `document_id`, `chunk_id`, `vector_id`, `artifact_id`, `metric`, `score`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`
- `POST /replay` → `matches`, `original_fingerprint`, `replay_fingerprint`, `details`, `nondeterministic_sources`, `execution_contract`, `execution_contract_status`, `replayable`, `execution_id`

## Canonical schemas
- API request schemas are frozen in `api/v1/schema.yaml`.
- The OpenAPI JSON is generated in `api/v1/openapi.v1.json`.

If you depend on a field, you can rely on this document and the schema file as the legal contract.
