# SSOT

Source-of-truth locations for `bijux-canon-runtime` are:
- `src/bijux_canon_runtime/` for implementation
- `apis/bijux-canon-runtime/v1/` for API contracts
- `src/bijux_canon_runtime/observability/schema.*` and migrations for execution-store schema
- `tests/` for executable runtime behavior
- `docs/*.md` here for package-local scope and boundaries

These files are authoritative for what runtime owns and what it deliberately does not own.
