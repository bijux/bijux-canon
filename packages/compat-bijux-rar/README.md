# bijux-rar

`bijux-rar` is a compatibility package that preserves the legacy distribution
and Python import surface.

Canonical package:
- `bijux-canon-reason`

Use this package only when an existing environment still depends on the legacy distribution name. New work should depend on `bijux-canon-reason` directly.

Canonical package links:
- package directory: [`../bijux-canon-reason`](../bijux-canon-reason)
- package docs: [`../bijux-canon-reason/docs/index.md`](../bijux-canon-reason/docs/index.md)

Compatibility package contents:
- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- `bijux_rar` Python module
- legacy `bijux-rar` CLI via `bijux-canon-reason`
