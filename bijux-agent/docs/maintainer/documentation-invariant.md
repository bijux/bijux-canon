# Documentation invariant (maintainer)

Documentation is checksum-tracked and test-enforced.

## Invariant

1. Every `docs/**/*.md` file MUST appear in `docs/doc_checksums.json`.
2. Every tracked file MUST be listed in `docs/index.md` as a `- docs/...` bullet.
3. Each tracked file’s SHA-256 MUST match the value in `docs/doc_checksums.json`.

## Workflow when editing docs

1. Edit docs.
2. Regenerate `docs/doc_checksums.json` (SHA-256 per file).
3. Ensure `docs/index.md` lists all tracked files.

The test enforcing this lives at `tests/invariants/test_documentation_invariant.py`.
