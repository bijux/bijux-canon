# EFFECTS

`bijux-canon-ingest` performs these important effects:
- reads source documents and request payloads
- writes retrieval/index artifacts and generated API snapshots
- may call embedder adapters through `infra/`
- emits HTTP responses, CLI output, and observability records

Pure transforms belong in `processing/` and retrieval logic. Filesystem, network, and adapter effects belong at boundaries.
