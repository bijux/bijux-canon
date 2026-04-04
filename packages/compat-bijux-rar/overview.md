# bijux-rar

Use this package only when an existing installation still expects the legacy
reasoning package name.

## What it does

- installs the canonical package `bijux-canon-reason`
- preserves the legacy `bijux_rar` Python import surface
- preserves the legacy `bijux-rar` command name

## Preferred install for new environments

```bash
pip install bijux-canon-reason
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-reason`
- Python import: `bijux_canon_reason`
- docs entrypoint: `packages/bijux-canon-reason/docs/index.md`
