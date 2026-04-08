# bijux-agent

Use this package only when an existing installation still depends on the legacy
agent package name. Each release continues the published `bijux-agent`
distribution and installs `bijux-canon-agent` at the same version.

The canonical package family now lives in `bijux-canon`, and the standalone
`https://github.com/bijux/bijux-agent` repository is scheduled for retirement
in favor of `https://github.com/bijux/bijux-canon`.

## What it does

- installs the canonical package `bijux-canon-agent`
- pins that canonical package to the same published version
- preserves the legacy `bijux_agent` Python import surface
- preserves the legacy `bijux-agent` command name

## Preferred install for new environments

```bash
uv add bijux-canon-agent
```

## Migration guidance

When updating callers, move to:

- distribution: `bijux-canon-agent`
- Python import: `bijux_canon_agent`
- legacy package handbook: `https://bijux.io/bijux-canon/compat-packages/bijux-agent/`
- docs entrypoint: `https://bijux.io/bijux-canon/bijux-canon-agent/`
- migration handbook: `https://bijux.io/bijux-canon/compat-packages/migration-guidance/`
