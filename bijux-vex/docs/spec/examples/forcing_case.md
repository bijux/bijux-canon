# Forcing scenario: ND ANN with budget exhaustion and replay divergence

**Steps (MUST):**

- Execute a NON_DETERMINISTIC ANN request with a strict budget (`max_vectors=0`, low latency).
- Allow partial execution; status MUST be `PARTIAL`.
- Fallback deterministic path MUST be used when ANN cannot proceed under budget.
- Replay MUST re-run the plan and detect divergence against the baseline fingerprint.

**Invariants (IDs):**

- INV-020: Randomness required for ND execution.
- INV-021: Budget exhaustion recorded, status PARTIAL.
- INV-010: Contract alignment enforced.
- INV-030: Plan fingerprint must not mutate between execution and replay.

**Expected behavior:**

- First run yields partial results and signature.
- Replay with the baseline fingerprint produces a different results fingerprint and details indicating nondeterministic divergence.
- Fallback path is exercised during replay to make divergence observable.
