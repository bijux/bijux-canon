# bijux-rar

Use this package only when an existing installation still expects the legacy
reasoning package name. Each release continues the published `bijux-rar`
distribution and installs `bijux-canon-reason` at the same version.

The canonical package family now lives in `bijux-canon`, and the standalone
`https://github.com/bijux/bijux-rar` repository is scheduled for retirement
in favor of `https://github.com/bijux/bijux-canon`.

## What it does

- installs the canonical package `bijux-canon-reason`
- pins that canonical package to the same published version
- preserves the legacy `bijux_rar` Python import surface
- preserves the legacy `bijux-rar` command name

## Preferred install for new environments

```bash
uv add bijux-canon-reason
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-reason`
- Python import: `bijux_canon_reason`
- legacy package handbook: `https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rar/`
- docs entrypoint: `https://bijux.io/bijux-canon/04-bijux-canon-reason/`
- migration handbook: `https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/`
