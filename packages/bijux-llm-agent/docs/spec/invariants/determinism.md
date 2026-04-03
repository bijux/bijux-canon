# Determinism invariants (spec)

## Replayability classification

- If `model_metadata.temperature > 0`, the trace header MUST set `replay_status = NON_REPLAYABLE`.
- If `model_metadata.temperature == 0`, the trace header SHOULD set `replay_status = REPLAYABLE`.

## Deterministic snapshots

- Trace entries MUST be serializable as JSON.
- Trace entries MUST allow a “deterministic snapshot” that excludes observational fields (e.g. timestamps).

## Observational fields

- Timestamps are observational and MUST NOT be used as determinism proofs.
- Adding new observational fields is allowed, but they should be explicitly classified.

## Hashing and fingerprints

- Run fingerprinting MUST hash a stable representation of:
  - pipeline definition
  - config snapshot
  - contract versions
- Hash computation MUST be order-stable (JSON canonicalization).
