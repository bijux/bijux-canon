# bijux-agent

`bijux-agent` is the compatibility package for the old agent distribution name.
Its purpose is to keep legacy environments working while the canonical package
name is `bijux-canon-agent`.

## Canonical package

- `bijux-canon-agent`

## What this compatibility package preserves

- the legacy distribution name `bijux-agent`
- the legacy Python import surface `bijux_agent`
- the legacy command name `bijux-agent`

## What to do for new work

Use `bijux-canon-agent` directly:

- package directory: [`../bijux-canon-agent`](../bijux-canon-agent)
- package docs: [`../bijux-canon-agent/docs/index.md`](../bijux-canon-agent/docs/index.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
