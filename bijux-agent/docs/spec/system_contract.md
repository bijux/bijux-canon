# System contract (spec)

## Scope

This contract applies to:

- the canonical pipeline (`AuditableDocPipeline`)
- the CLI driver (`python -m bijux_agent.main run …`)
- the API v1 handler (`POST /v1/run`)
- produced artifacts (result + trace)

It does **not** guarantee anything about model “correctness”, cost, or latency.

## Core guarantees

### Canonical pipeline

- The canonical pipeline structure (phase order and allowed transitions) MUST be fixed at runtime.
- Runs MUST record enough metadata to identify:
  - the pipeline definition used,
  - the config snapshot used,
  - the runtime version used.

### Trace safety

- A trace MUST record a `trace_schema_version`.
- A trace MUST record the runtime version (`runtime_version`).
- A trace MUST record `model_metadata` (provider, model name, temperature, max tokens).

### Replayability classification

- Traces MUST be marked **NON_REPLAYABLE** when `model_metadata.temperature > 0`.
- Consumers MUST NOT treat a NON_REPLAYABLE trace as eligible for deterministic replay validation.

### Fail-fast behavior

The system MUST fail fast when:

- required trace metadata is missing,
- failure taxonomy is violated (invalid `FailureArtifact`),
- a trace payload cannot be validated against the current schema (or upgraded).

## Compatibility rules

- Schema versions are the compatibility gate. Breaking changes require a version bump.
- Consumers MUST tolerate additional fields in JSON payloads (forward-compatible parsing).

For artifact details: `docs/spec/execution_artifacts.md`.
