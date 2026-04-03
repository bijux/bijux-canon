# Architecture

This document is a module-level map of the codebase. It describes *where responsibilities live*, not every implementation detail.

## Top-level components

### CLI (`src/bijux_canon_agent/__main__.py`, `src/bijux_canon_agent/interfaces/cli/`)

- Parses arguments (`run`, `replay`)
- Loads config + environment
- Invokes the canonical pipeline (`AuditableDocPipeline`)
- Writes run artifacts (`final_result.json`, `run_trace.json`)

### HTTP API (`src/bijux_canon_agent/api/`, `src/bijux_canon_agent/api/v1/`)

- `api/v1/app.py` exposes the package ASGI app and `api/v1/http.py` exposes a small FastAPI router
- `src/bijux_canon_agent/api/v1/*` owns request/response schemas and the execution handler
- The v1 handler is intentionally narrow: it runs the canonical pipeline with a minimal config baseline

### Pipeline core (`src/bijux_canon_agent/pipeline/`)

- **Canonical pipeline**: `pipeline/canonical.py` defines `AuditableDocPipeline`
- **Lifecycle semantics**: `pipeline/control/*` defines lifecycle rules and stop reasons
- **Execution**: `pipeline/execution/*` (agent calls, retries, timeouts)
- **Results**: `pipeline/results/*` defines structured decision/failure artifacts
- **Convergence**: `pipeline/convergence/*` defines convergence detection semantics

### Application (`src/bijux_canon_agent/application/`)

- `application/orchestration/*` owns deterministic orchestration policies and state machines

### Tracing (`src/bijux_canon_agent/traces/`)

- Trace schema, validation, and upgrades
- Field classification (deterministic vs observational)
- Run fingerprinting (pipeline definition + config snapshot hashing)

### LLM Runtime (`src/bijux_canon_agent/llm/`)

- Adapter registry and contracts for LLM backends
- LLM runtime helpers for provider-facing execution support
- A strict output contract (`AgentOutputSchema`) to keep downstream logic stable

### Support (`src/bijux_canon_agent/observability/`, `src/bijux_canon_agent/core/`)

- Observability owns structured logging and telemetry plumbing
- Support owns small shared helpers such as hashing, final decorators, and version helpers

### Configuration (`src/bijux_canon_agent/config/`)

- Defaults and minimal example configs
- Environment key loading/validation (`src/bijux_canon_agent/config/env.py`)
- Example runtime YAML (`examples/reference-config.yml`)

### Examples (`src/bijux_canon_agent/reference_pipelines/`)

- Example pipelines intended for adoption, docs, and smoke coverage

## Data flow

1. CLI or API constructs a *context* (`task_goal`, input, identifiers).
2. `AuditableDocPipeline.run(context)` orchestrates lifecycle steps and agent calls.
3. Results are normalized into a final decision, plus trace metadata.
4. The CLI writes:
   - `result/final_result.json` (human-facing summary)
   - `trace/run_trace.json` (audit trail)

## Extension points (and boundaries)

Supported extension points:

- adding new agents via the agent registry
- adding a model adapter (provider) behind the existing contracts

Explicitly *not* supported (by design):

- dynamic pipeline composition at runtime
- stateful cross-run memory
- silent retries without a declared policy

See the formal non-goals: `docs/spec/refusals.md`.
