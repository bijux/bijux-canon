# Project Overview

`bijux-canon-agent` is an auditable pipeline runtime. Its job is to run a fixed lifecycle, coordinate agents, emit trace-backed artifacts, and expose that behavior through CLI and HTTP boundaries.

## Ideal tree

- `src/bijux_canon_agent/application/`
  Runtime orchestration owned by the package, including workflow-graph execution policy.
- `src/bijux_canon_agent/agents/`
  Agent implementations and their local kernels, with per-agent input/reporting helpers kept beside the core class instead of folded into monolith files.
- `src/bijux_canon_agent/pipeline/`
  Canonical lifecycle, execution flow, trace semantics, and final-result assembly.
- `src/bijux_canon_agent/interfaces/`
  CLI entrypoints and user-facing serialization helpers.
- `src/bijux_canon_agent/api/`
  HTTP surface and request/response schemas.
- `src/bijux_canon_agent/observability/`
  Logging and telemetry plumbing.
- `src/bijux_canon_agent/config/`
  Runtime defaults and environment handling.
- `src/bijux_canon_agent/tooling/example_pipelines/`
  Importable example builders used in docs and smoke coverage.
- `examples/`
  Human-run sample assets such as `reference-config.yml` and golden outputs.
- `config/execution_policy.yaml`
  Repository-managed execution policy for retries, fallback, scope reduction, and abort behavior.
- `tests/`
  Unit, API, invariant, and end-to-end coverage.

## Boundary rules

- Keep runtime artifacts under `artifacts/` or test fixtures, never under `src/`.
- Keep product-specific workflows out of this package; this package provides reusable runtime behavior.
- Keep agent result shaping, telemetry access, and schema-report helpers in focused modules such as `interfaces/cli/*`, `observability/*`, and `agents/*/reporting.py` or `agents/*/inputs.py`.
- Keep docs and package metadata aligned with the real tree so the package can be understood without archaeology.
