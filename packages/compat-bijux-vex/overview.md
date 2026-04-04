# bijux-vex

Use this package only when an existing installation still expects the legacy
index package name.

## What it does

- installs the canonical package `bijux-canon-index`
- preserves the legacy `bijux_vex` Python import surface
- preserves the legacy `bijux-vex` command name

## Preferred install for new environments

```bash
pip install bijux-canon-index
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-index`
- Python import: `bijux_canon_index`
- docs entrypoint: `packages/bijux-canon-index/docs/index.md`
