# agentic-flows

Use this package only when an existing environment still expects the legacy
runtime name. Each release continues the published `agentic-flows`
distribution and installs `bijux-canon-runtime` at the same version.

## What it does

- installs the canonical runtime package `bijux-canon-runtime`
- pins that canonical runtime package to the same published version
- preserves the legacy `agentic_flows` Python import surface
- preserves the legacy `agentic-flows` command name

## Preferred install for new environments

```bash
pip install bijux-canon-runtime
```

## Migration guidance

If you are updating scripts or dependencies, prefer changing them to:

- distribution: `bijux-canon-runtime`
- Python import: `bijux_canon_runtime`
- docs entrypoint: `packages/bijux-canon-runtime/docs/index.md`
