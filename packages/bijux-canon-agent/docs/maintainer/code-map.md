# Code map

High-signal locations:

- `src/bijux_canon_agent/main.py` — CLI entry point
- `src/bijux_canon_agent/cli/` — CLI helpers and artifact writing
- `src/bijux_canon_agent/httpapi/` — FastAPI integration layer
- `src/bijux_canon_agent/api/v1/` — v1 schemas and handlers
- `src/bijux_canon_agent/pipeline/` — canonical pipeline, phases, execution, results
- `src/bijux_canon_agent/tracing/` — trace schema, validation, upgrades, fingerprints
- `tests/` — unit tests and invariants (docs coverage, contract checks)

If you touch `docs/spec/*`, assume you are changing the contract.
