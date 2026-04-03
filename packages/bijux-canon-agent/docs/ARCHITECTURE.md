# ARCHITECTURE

`bijux-canon-agent` is a deterministic agent-pipeline package.

Core layout:
- `src/bijux_canon_agent/agents/` implements agent roles and role-local helpers.
- `src/bijux_canon_agent/pipeline/` owns lifecycle, execution flow, termination, and result shaping.
- `src/bijux_canon_agent/application/` owns orchestration policies that coordinate the pipeline.
- `src/bijux_canon_agent/interfaces/cli/` and `src/bijux_canon_agent/api/v1/` expose the operator boundaries.
- `src/bijux_canon_agent/observability/`, `traces/`, and `config/` support telemetry, replay, and configuration.

The intended architecture is thin boundaries over a durable pipeline core. Agent implementations belong beside their own input, reporting, and validation helpers rather than inside cross-cutting monolith files.
