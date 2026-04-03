# Embedding Lifecycle

Embeddings are data with provenance. They must be explicit and auditable.

Embedding providers

- Providers are selected explicitly by name.
- No implicit model selection is allowed.

Caching rules

- Cache is off by default.
- Cache keys include model id, provider version, and normalization settings.

Determinism implications

- Providers must declare deterministic or non-deterministic behavior.
- ND embedding providers require explicit randomness declaration.

Metadata captured

- Provider name, model id, model version, dtype, device, and seed.

Failure handling

- Embedding failure is atomic. No partial ingest is written.

Ingest example

```bash
bijux vex ingest --doc "hello" \
  --embed-provider sentence-transformers \
  --embed-model all-MiniLM-L6-v2 \
  --vector-store memory
```
