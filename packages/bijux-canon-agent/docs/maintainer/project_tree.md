# Project tree

High-signal directories:

- `src/bijux_agent/` — library and runtime code
- `tests/` — unit + invariant tests
- `docs/` — MkDocs sources (this directory)
- `examples/default-config.yml` — example runtime configuration for CLI runs
- `failure_policy.yaml` — package-managed retry, fallback, scope, and abort rules
- `../../apis/bijux-canon-agent/` — root-managed OpenAPI schema and API assets
- `../../makes/bijux-agent/` — Make targets used by CI and developers

Generated artifacts belong under `artifacts/bijux-canon-agent/` (or under the CLI `--out` directory).
