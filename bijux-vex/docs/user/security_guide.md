# Security Guide

## Secrets Handling

- Use environment variables or secret managers for backend credentials.
- Vector store URIs are redacted in logs and provenance.

## Provenance Redaction

- `vector_store.uri_redacted` is stored instead of raw URIs.
- Bundle exports use redacted config by default.

## Safe Bundle Sharing

- Bundles include provenance, config (redacted), and results.
- Vectors are excluded unless `--include-vectors` is explicitly set.

## Threat Model Boundaries

Bijux Vex does **not**:

- Prevent malicious data in vectors or documents.
- Validate external service credentials beyond connectivity.
- Provide encryption at rest for local files.

Bijux Vex **does**:

- Enforce explicit configuration for vector stores and embeddings.
- Refuse deterministic runs when determinism cannot be guaranteed.
