# Concepts

This project exists to make LLM-backed document processing *auditable*. The core design choice is that a run must leave behind artifacts that can be inspected, diffed, and validated.

## Pipeline as a contract

A run is an execution of the canonical pipeline (`AuditableDocPipeline`) over a *context*:

- a goal (`task_goal`)
- an input (`text` or a `file_path`)
- a stable identifier (`context_id`)

The pipeline is **canonical**: its phase order and allowed transitions are fixed and versioned. Consumers should assume “same inputs + same config + same model settings” implies “same trace classification”, not “same model output”.

## Phases

The canonical lifecycle is:

`INIT → PLAN → EXECUTE → JUDGE → VERIFY → FINALIZE → DONE`

Not every phase necessarily produces user-visible content today, but the lifecycle exists so traces have a stable semantic scaffold.

## Artifacts and why they matter

A normal CLI run writes two primary artifacts:

- `result/final_result.json` — a compact verdict summary (what you would read first)
- `trace/run_trace.json` — the trace (what you audit and validate)

The trace is designed to support:

- post-hoc debugging (“why did we decide PASS?”),
- regression detection (compare fingerprints across versions),
- replay validation (“does this trace satisfy the contract?”).

## Determinism vs replayability

Determinism is treated as a *classification*, not a promise that LLM sampling will match across time.

The system marks traces:

- **REPLAYABLE** when `model_metadata.temperature == 0.0`
- **NON_REPLAYABLE** otherwise

Replayability controls what the tooling is allowed to claim, not what the user is allowed to do.

## Failure semantics (high-level)

Failures are represented by an immutable `FailureArtifact`:

- a machine-actionable class (`failure_class`)
- an operational/epistemic category
- recoverability (whether the orchestrator may attempt recovery)

See the formal taxonomy: `docs/spec/failure_model.md`.

## Where to go next

- For hands-on usage: `docs/user/usage.md`
- For the formal contract: `docs/spec/read_this_first.md`
