# Execution artifacts (spec)

## Artifact set

A normal CLI run writes these primary artifacts under `--out <RUN_DIR>`:

- `result/final_result.json`
- `trace/run_trace.json`

Additional logs may be written to the directory configured in `logging.log_dir`.

## `final_result.json` (verdict summary)

This artifact is the first thing a human should read.

It MUST include:

- `verdict` (string; decision outcome)
- `confidence` (float)
- `epistemic_status` (string)
- `runtime_version` (string)
- `termination_reason` (string)

It SHOULD include:

- `trace_path` (relative path to `run_trace.json` when a trace exists)
- convergence fields (`converged`, `convergence_reason`, `convergence_iterations`)
- `model_metadata` (when available)

## `run_trace.json` (audit trace)

A trace MUST include:

- a header with `trace_schema_version`
- `runtime_version`
- `model_metadata`
- at least one trace entry

Trace entries MAY include:

- `replay_metadata` and run fingerprints (to identify inputs/config/pipeline)
- structured failure and decision artifacts
- observational timing fields (timestamps)

## Forward compatibility

- Producers MAY add new fields.
- Consumers MUST ignore unknown fields.
- Breaking changes MUST bump the trace schema version.

See also:

- `docs/spec/identity.md` (versioning and identity)
- `docs/spec/invariants/determinism.md` (deterministic vs observational fields)
