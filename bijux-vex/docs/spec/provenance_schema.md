# Provenance Schema (extension)

Provenance is the audit surface for execution results. The schema is **additive** and explicit.

## New fields (v0.2.0)
The provenance output may include:

- `embedding_source`
- `embedding_determinism`
- `embedding_seed`
- `embedding_model_version`
- `embedding_provider`
- `embedding_device`
- `embedding_dtype`
- `vector_store_backend`
- `vector_store_uri_redacted`
- `vector_store_index_params`
- `execution_contract_status` (stable vs experimental)

These fields are optional today because not every run uses embeddings or a vector store, but the schema is reserved.

## Where provenance appears
- `explain_result` output (CLI/API `explain` flow)
- Stored execution results for replay and audit

## Compatibility
This is an additive extension: v0.1.x readers should tolerate missing fields; v0.2.x guarantees the fields are present (may be `null`).
