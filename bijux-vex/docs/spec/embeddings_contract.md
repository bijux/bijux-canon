# Embedding Generation Contract

Embedding generation is a **contracted step**, not a hidden side-effect.
It may be deterministic or non-deterministic, but it must always surface provenance.

## Rules
- Embedding generation must be explicitly invoked; no implicit embedding creation.
- Deterministic embeddings must be reproducible under a declared model/version.
- Non-deterministic embeddings must declare randomness sources and bounds.
- If vectors are omitted, `--embed-model` (or API `embed_model`) is required.
- The default local provider is `sentence_transformers` (optional extra).
- Embedding caching is opt-in only (`--cache-embeddings`); no implicit cache.

## Provenance requirements
Every embedding step must emit the following metadata (see provenance schema extension):

- `embedding_source`
- `embedding_determinism`
- `embedding_seed`
- `embedding_model_version`
- `embedding_provider`
- `embedding_device`
- `embedding_dtype`

## Status
Embedding generation is available via the local sentence-transformers provider when explicitly enabled.
