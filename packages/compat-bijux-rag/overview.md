# bijux-rag

Use this package only when an existing environment still expects the legacy
ingest package name. Each release continues the published `bijux-rag`
distribution and installs `bijux-canon-ingest` at the same version.

## What it does

- installs the canonical package `bijux-canon-ingest`
- pins that canonical package to the same published version
- preserves the legacy `bijux_rag` Python import surface
- preserves the legacy `bijux-rag` command name

## Preferred install for new environments

```bash
pip install bijux-canon-ingest
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-ingest`
- Python import: `bijux_canon_ingest`
- docs entrypoint: `packages/bijux-canon-ingest/docs/index.md`
