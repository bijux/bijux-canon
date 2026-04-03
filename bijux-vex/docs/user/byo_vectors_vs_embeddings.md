# BYO Vectors vs Auto-Embeddings

Bijux-Vex treats **user-provided vectors** as the primary, most explicit workflow. Auto-embeddings are available, but only when you opt in with an explicit model.

## Bring Your Own Vectors (Recommended for control)
- Maximum determinism: you control the embedding model, version, and runtime.
- Full auditability: vectors can be regenerated outside Bijux-Vex.
- No hidden costs or persistence.

## Auto-Embeddings (Explicit opt-in)
- Convenience: provide documents only and specify `--embed-model`.
- Provider-specific determinism: some providers are deterministic only under certain devices/versions.
- Provenance is captured (provider, model version, device, dtype).

## Decision Guide
- Choose **BYO vectors** when reproducibility, auditability, or model governance matters.
- Choose **auto-embeddings** when speed and simplicity outweigh strict determinism.

## CLI Examples
Provide vectors explicitly:
```bash
bijux vex ingest --doc "hello" --vector "[0.1,0.2,0.3]"
```

Auto-embed explicitly:
```bash
bijux vex ingest --doc "hello" --embed-model "all-MiniLM-L6-v2"
```

Optional caching:
```bash
bijux vex ingest --doc "hello" --embed-model "all-MiniLM-L6-v2" --cache-embeddings sqlite
```

Note: auto-embeddings require the optional `embeddings` extra (`sentence-transformers`).
