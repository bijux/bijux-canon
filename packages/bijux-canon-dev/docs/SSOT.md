# Source Of Truth

## Authoritative locations

- `src/bijux_canon_dev/` for implementation
- `tests/` for executable behavior
- `docs/` for ownership and change guidance
- root `Makefile`, `makes/`, and CI workflows for real call sites

## How to resolve ambiguity

1. Look at the live root caller to understand how the helper is used.
2. Look at the implementation to understand what it currently does.
3. Look at tests to see what behavior is intentionally protected.
4. Look at package docs to understand what should belong here long term.

If a repository behavior still needs to exist but currently lives in a shell
fragment, an ad-hoc CI step, or a copied script, this package is the first home
to consider.
