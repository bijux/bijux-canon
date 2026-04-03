# agentic-flows

`agentic-flows` is a compatibility package that preserves the legacy distribution,
CLI, and Python import surface.

Canonical package:
- `bijux-canon-runtime`

Use this package only when an existing environment still depends on the legacy
distribution name. New work should depend on `bijux-canon-runtime` directly.

Canonical package links:
- package directory: [`../bijux-canon-runtime`](../bijux-canon-runtime)
- package docs: [`../bijux-canon-runtime/docs/index.md`](../bijux-canon-runtime/docs/index.md)

Compatibility package contents:
- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- `agentic_flows` Python module
- `agentic-flows` console command
