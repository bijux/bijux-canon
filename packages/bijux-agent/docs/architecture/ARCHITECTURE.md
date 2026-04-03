# Architecture

This document is a module-level map of the codebase. It describes *where responsibilities live*, not every implementation detail.

## Top-level components

### CLI (`src/bijux_agent/main.py`, `src/bijux_agent/cli/`)

- Parses arguments (`run`, `replay`)
- Loads config + environment
- Invokes the canonical pipeline (`AuditableDocPipeline`)
- Writes run artifacts (`final_result.json`, `run_trace.json`)

### HTTP API (`src/bijux_agent/httpapi/`, `src/bijux_agent/api/v1/`)

- `httpapi/v1.py` exposes a small FastAPI router (when FastAPI is installed)
- `api/v1/*` owns request/response schemas and the execution handler
- The v1 handler is intentionally narrow: it runs the canonical pipeline with a minimal config baseline

### Pipeline core (`src/bijux_agent/pipeline/`)

- **Canonical pipeline**: `pipeline/canonical.py` defines `AuditableDocPipeline`
- **Lifecycle semantics**: `pipeline/control/*` defines phases and stop reasons
- **Execution**: `pipeline/execution/*` (agent calls, retries, timeouts)
- **Results**: `pipeline/results/*` defines structured decision/failure artifacts
- **Convergence**: `pipeline/convergence/*` defines convergence detection semantics

### Tracing (`src/bijux_agent/tracing/`)

- Trace schema, validation, and upgrades
- Field classification (deterministic vs observational)
- Run fingerprinting (pipeline definition + config snapshot hashing)

### Models (`src/bijux_agent/models/`)

- Adapter registry and contracts for LLM backends
- A strict output contract (`AgentOutputSchema`) to keep downstream logic stable

### Configuration (`src/bijux_agent/config/`)

- Defaults and minimal reference configs
- Environment key loading/validation (`config/env.py`)

## Data flow

1. CLI or API constructs a *context* (`task_goal`, input, identifiers).
2. `AuditableDocPipeline.run(context)` orchestrates phases and agent calls.
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
