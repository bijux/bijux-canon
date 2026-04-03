# CONTRACTS

Stable contracts in `bijux-canon-agent` are:
- the console entrypoint `bijux-canon-agent`
- the API surface under `src/bijux_canon_agent/api/v1/`
- trace and final-result artifact shapes under `src/bijux_canon_agent/traces/` and `src/bijux_canon_agent/core/`
- configuration and environment contracts under `src/bijux_canon_agent/config/`

Public contracts should change intentionally, with tests and docs updated together. Internal helpers may move as long as they do not break these package-facing surfaces.
