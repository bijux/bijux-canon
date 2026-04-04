# agentic-flows

Use this package only when an existing environment still expects the legacy
runtime name.

## What it does

- installs the canonical runtime package `bijux-canon-runtime`
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
