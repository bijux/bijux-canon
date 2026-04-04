# bijux-rar

Use this package only when an existing installation still expects the legacy
reasoning package name. Each release continues the published `bijux-rar`
distribution and installs `bijux-canon-reason` at the same version.

## What it does

- installs the canonical package `bijux-canon-reason`
- pins that canonical package to the same published version
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
