# Do not optimize (by design)

These are intentionally “heavy” and must stay that way:

- Canon normalization and fingerprinting: preserve provenance integrity.
- Invariant checks: fail fast; do not bypass or “retry” invariants.
- Execution state machine: explicit transitions prevent ghost states.
- Replay requiring provenance: no shortcuts; missing provenance must fail.
- ND refusal without ANN: keeps contracts honest; no silent fallback.

Optimizing away these checks is a correctness regression.
