# Rejected design alternatives

These are intentionally rejected to prevent future regressions.

- **VDB-style CRUD APIs**: rejected; bijux-vex is an execution engine, not storage. Silent persistence semantics would dilute contracts.
- **Implicit retries on invariants**: rejected; invariants are terminal programmer/system faults. Retrying hides bugs and corrupts provenance.
- **Silent ND fallback to deterministic**: rejected; violates declared contracts. ND without ANN must fail explicitly.
- **Hidden randomness**: rejected; all randomness must be declared via `RandomnessProfile` and audited.
- **Adaptive schema drift**: rejected; OpenAPI/ABI changes require additive evolution or version bumps, never silent drift.
