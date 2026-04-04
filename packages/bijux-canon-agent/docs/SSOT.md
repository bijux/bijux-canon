# Source Of Truth

Use the nearest durable source instead of guessing from summaries.

## Authoritative locations

- `src/bijux_canon_agent/` for implementation behavior
- `tests/` for executable expectations and regression protection
- `docs/` for package-local ownership, architecture, and change guidance
- `pyproject.toml` for package metadata and declared entrypoints

## Preferred order when docs and code disagree

1. tests for observed behavior
2. code for current implementation
3. package docs for intended design and ownership
4. root docs for repository-wide summaries

When the lower-level sources disagree with the docs, fix the docs or the code in
the same review instead of leaving the mismatch behind.
