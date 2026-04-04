# bijux-vex

`bijux-vex` is the compatibility package for the old index distribution name.
Its purpose is to keep legacy installs and imports working while the canonical
package name is `bijux-canon-index`.

## Canonical package

- `bijux-canon-index`

## What this compatibility package preserves

- the legacy distribution name `bijux-vex`
- the legacy Python import surface `bijux_vex`
- the legacy command name `bijux-vex`

## What to do for new work

Use `bijux-canon-index` directly:

- package directory: [`../bijux-canon-index`](../bijux-canon-index)
- package docs: [`../bijux-canon-index/docs/index.md`](../bijux-canon-index/docs/index.md)

## Package contents

- [pyproject.toml](pyproject.toml)
- [hatch_build.py](hatch_build.py)
- [overview.md](overview.md)
- [CHANGELOG.md](CHANGELOG.md)
