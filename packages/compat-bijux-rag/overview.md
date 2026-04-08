# bijux-rag

Use this package only when an existing environment still expects the legacy
ingest package name. Each release continues the published `bijux-rag`
distribution and installs `bijux-canon-ingest` at the same version.

The canonical package family now lives in `bijux-canon`, and the standalone
`https://github.com/bijux/bijux-rag` repository is scheduled for retirement
in favor of `https://github.com/bijux/bijux-canon`.

## What it does

- installs the canonical package `bijux-canon-ingest`
- pins that canonical package to the same published version
- preserves the legacy `bijux_rag` Python import surface
- preserves the legacy `bijux-rag` command name

## Preferred install for new environments

```bash
uv add bijux-canon-ingest
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-ingest`
- Python import: `bijux_canon_ingest`
- legacy package handbook: `https://bijux.io/bijux-canon/compat-packages/bijux-rag/`
- docs entrypoint: `https://bijux.io/bijux-canon/bijux-canon-ingest/`
- migration handbook: `https://bijux.io/bijux-canon/compat-packages/migration-guidance/`
