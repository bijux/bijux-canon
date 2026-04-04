# Effects

The package touches files, requests, adapters, and generated artifacts, so its
effects need to stay understandable.

## Main side effects

- reading source documents and request payloads
- writing ingest and retrieval artifacts
- calling embedder or integration adapters
- emitting HTTP responses, CLI output, and observability records

## Guardrails

- deterministic transforms should stay separate from I/O code
- filesystem, network, and adapter effects should stay near boundaries and adapters
- ingest outputs should remain explainable after the fact
