# Determinism (design notes)

Determinism is a design constraint for *auditability*, not a promise that two LLM runs will always yield byte-identical text.

## What “deterministic” means here

A run is *structurally deterministic* when:

- the pipeline phase order and allowed transitions are fixed,
- the run configuration is captured and fingerprinted,
- all trace-critical metadata is recorded,
- the system can classify replayability honestly.

The system treats LLM sampling as inherently unstable unless explicitly constrained.

## Replayability classification

The trace header records a `replay_status`:

- **REPLAYABLE** when `model_metadata.temperature == 0.0`
- **NON_REPLAYABLE** otherwise

A trace may still be *auditable* even when it is non-replayable.

## Deterministic vs observational trace fields

Some fields exist for operations and debugging, but cannot be stable across runs
(e.g. timestamps). The trace schema classifies fields as:

- **deterministic**: must be stable for replay validation
- **observational**: allowed to drift (e.g. `start_time`, `end_time`)

Consumers should avoid asserting on observational fields.

## Practical guardrails

If you want maximal determinism:

- set `model_metadata.temperature: 0.0`
- avoid time-dependent prompts and external calls
- treat inputs as immutable snapshots (the CLI already writes a file snapshot for API inputs)
- do not mutate pipeline phase composition at runtime

For the normative version of these rules, see `docs/spec/invariants/determinism.md`.
