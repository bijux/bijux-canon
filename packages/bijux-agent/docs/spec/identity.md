# Identity and versioning (spec)

A trace is only useful if a consumer can identify *what produced it*.

## Required identifiers

Traces and/or artifacts MUST record:

- `trace_schema_version` — compatibility gate for `run_trace.json`
- `runtime_version` — the package/runtime version producing the artifact
- `model_metadata` — provider, model name, temperature, max tokens

Trace entries and replay metadata MAY record:

- `contract_version` — system contract version
- `agent_contract_version` — agent output contract version
- `model_id` / hashes — stable identifiers for deterministic classification
- a run fingerprint capturing pipeline definition + config snapshot

## Schema upgrade rule

When reading a trace:

- If the schema version is older and an upgrade path exists, tooling SHOULD upgrade in-memory.
- If an upgrade path does not exist, tooling MUST reject the trace as incompatible.

## Replayability rule

- If `model_metadata.temperature > 0`, the trace MUST be marked `NON_REPLAYABLE`.
- Consumers MUST treat replayability as a property of the *trace*, not a guess about the model.

See also: `docs/spec/invariants/determinism.md`.
