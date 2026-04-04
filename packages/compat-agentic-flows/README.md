# agentic-flows

`agentic-flows` is a compatibility package for the old runtime distribution
name. Its job is to keep legacy installs and imports working while the canonical
package name is `bijux-canon-runtime`.

This package exists to reduce migration breakage, not to become the preferred
entrypoint for new work.

## Canonical package

- `bijux-canon-runtime`

## What this compatibility package preserves

- the legacy distribution name `agentic-flows`
- the legacy Python import surface `agentic_flows`
- the legacy command name `agentic-flows`

## What to do for new work

Depend on `bijux-canon-runtime` directly and read the canonical docs there:

- package directory: [`../bijux-canon-runtime`](../bijux-canon-runtime)
- package docs: [`../bijux-canon-runtime/docs/index.md`](../bijux-canon-runtime/docs/index.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
