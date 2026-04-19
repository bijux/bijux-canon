# agentic-flows

Use this package only when an existing environment still expects the legacy
runtime name. Each release continues the published `agentic-flows`
distribution and installs `bijux-canon-runtime` at the same version.

The canonical package family now lives in `bijux-canon`, and the standalone
`https://github.com/bijux/agentic-flows` repository is scheduled for
retirement in favor of `https://github.com/bijux/bijux-canon`.

## What it does

- installs the canonical runtime package `bijux-canon-runtime`
- pins that canonical runtime package to the same published version
- preserves the legacy `agentic_flows` Python import surface
- preserves the legacy `agentic-flows` command name

## Preferred install for new environments

```bash
uv add bijux-canon-runtime
```

## Migration guidance

If you are updating scripts or dependencies, prefer changing them to:

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- legacy package handbook: `https://bijux.io/bijux-canon/08-compat-packages/catalog/agentic-flows/`
- docs entrypoint: `https://bijux.io/bijux-canon/bijux-canon-runtime/`
- migration handbook: `https://bijux.io/bijux-canon/08-compat-packages/migration/migration-guidance/`
