# bijux-vex

Use this package only when an existing installation still expects the legacy
index package name. Each release continues the published `bijux-vex`
distribution and installs `bijux-canon-index` at the same version.

The canonical package family now lives in `bijux-canon`, and the standalone
`https://github.com/bijux/bijux-vex` repository is scheduled for retirement
in favor of `https://github.com/bijux/bijux-canon`.

## What it does

- installs the canonical package `bijux-canon-index`
- pins that canonical package to the same published version
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
- docs entrypoint: `https://bijux.io/bijux-canon/bijux-canon-index/`
- migration handbook: `https://bijux.io/bijux-canon/compat-packages/migration-guidance/`
