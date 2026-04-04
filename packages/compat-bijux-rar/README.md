# bijux-rar

`bijux-rar` is the compatibility package for the old reasoning distribution
name. It exists so older environments can keep working while the canonical
package name is `bijux-canon-reason`.

## Canonical package

- `bijux-canon-reason`

## What this compatibility package preserves

- the legacy distribution name `bijux-rar`
- the legacy Python import surface `bijux_rar`
- the legacy command name `bijux-rar` via the canonical package

## What to do for new work

Use `bijux-canon-reason` directly:

- package directory: [`../bijux-canon-reason`](../bijux-canon-reason)
- package docs: [`../bijux-canon-reason/docs/index.md`](../bijux-canon-reason/docs/index.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
