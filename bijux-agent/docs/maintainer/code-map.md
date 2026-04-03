# Code map

High-signal locations:

- `src/bijux_agent/main.py` — CLI entry point
- `src/bijux_agent/cli/` — CLI helpers and artifact writing
- `src/bijux_agent/httpapi/` — FastAPI integration layer
- `src/bijux_agent/api/v1/` — v1 schemas and handlers
- `src/bijux_agent/pipeline/` — canonical pipeline, phases, execution, results
- `src/bijux_agent/tracing/` — trace schema, validation, upgrades, fingerprints
- `tests/` — unit tests and invariants (docs checksums, contract checks)

If you touch `docs/spec/*`, assume you are changing the contract.
