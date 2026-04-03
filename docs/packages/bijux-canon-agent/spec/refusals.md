# Refusals and non-features (spec)

These are intentional non-goals. Treat them as stability promises.

## Stateful behavior

- The system MUST NOT persist cross-run memory by default.
- The system MUST NOT mutate previously written artifacts in-place.

## Hidden execution

- The orchestrator MUST NOT apply silent retries without an explicit failure policy.
- The system MUST NOT “auto-fix” invalid traces; invalid traces are rejected.

## Dynamic composition

- The canonical pipeline MUST NOT allow runtime mutation of phase order or transitions.
- The system MUST NOT accept arbitrary user-defined pipeline graphs at runtime.

## Misleading claims

- Dry-run MUST NOT claim model-derived output.
- NON_REPLAYABLE traces MUST NOT be presented as deterministically replayable.
