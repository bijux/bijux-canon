# Documentation invariant (maintainer)

Documentation coverage is index-tracked and test-enforced.

## Invariant

1. Every `docs/**/*.md` file MUST be listed in `docs/index.md` as a `- docs/...` bullet.
2. `docs/index.md` MUST NOT reference missing documentation files.

## Workflow when editing docs

1. Edit docs.
2. Ensure `docs/index.md` lists all tracked files.

The test enforcing this lives at `tests/invariants/test_documentation_invariant.py`.
