# bijux-agent

Use this package only when an existing installation still depends on the legacy
agent package name. Each release continues the published `bijux-agent`
distribution and installs `bijux-canon-agent` at the same version.

## What it does

- installs the canonical package `bijux-canon-agent`
- pins that canonical package to the same published version
- preserves the legacy `bijux_agent` Python import surface
- preserves the legacy `bijux-agent` command name

## Preferred install for new environments

```bash
python -m pip install bijux-canon-agent
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- docs entrypoint: `packages/bijux-canon-agent/docs/index.md`
