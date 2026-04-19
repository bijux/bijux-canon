# Source Of Truth

## Authoritative locations

- `src/bijux_canon_index/` for implementation
- `apis/03-bijux-canon-index/v1/` for pinned API contracts
- `tests/` and plugin tests for executable conformance
- `docs/` for package-local intent and ownership

## Preferred order when checking a claim

1. Look at tests and schemas for the currently enforced contract.
2. Look at the implementation for current behavior.
3. Look at these docs for design intent and boundaries.

Package-local docs should win over higher-level repository summaries when the
question is specifically about index behavior or ownership.
