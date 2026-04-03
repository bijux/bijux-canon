# Code map

High-signal locations:

- `src/bijux_canon_agent/__main__.py` — package CLI launcher
- `src/bijux_canon_agent/interfaces/cli/` — CLI boundary and artifact writing
- `src/bijux_canon_agent/api/` — ASGI app and HTTP boundary surface
- `src/bijux_canon_agent/api/v1/` — v1 schemas and handlers
- `src/bijux_canon_agent/application/` — orchestration policies and state machines
- `src/bijux_canon_agent/pipeline/` — canonical pipeline, lifecycle control, execution, results
- `src/bijux_canon_agent/reference_pipelines/` — reference pipeline builders
- `src/bijux_canon_agent/observability/` — logging and telemetry helpers
- `src/bijux_canon_agent/core/` — hashing, final markers, and version helpers
- `src/bijux_canon_agent/traces/` — trace schema, validation, upgrades, fingerprints
- `tests/` — unit tests and invariants (docs coverage, contract checks)

If you touch `docs/spec/*`, assume you are changing the contract.
