# Non-Determinism Contract

This system allows non-determinism only when it is declared, bounded, and approved by policy.
If you want randomness, you must ask for it explicitly and stay inside the guardrails.

## Allowed

- Declared non-determinism intent with a source, magnitude range, and justification.
- Declared entropy budgets that bound magnitude per source.
- Replay modes that state how divergence is evaluated (strict, bounded, observational).

## Forbidden

- Entropy without a declared intent.
- Entropy sources not listed in the policy or budget.
- Entropy magnitudes outside the declared range.

## Governance

- A non-determinism policy runs before execution.
- Policy violations hard-fail the run.
- Budget exhaustion triggers the configured action (halt, degrade, or mark non-certifiable).

## Guarantees That Still Hold

- Dataset identity, plan hash, and environment fingerprints are enforced.
- Replay acceptability is still validated against declared thresholds.
- Determinism profiles and entropy records are persisted for audit.

## Intentionally Not Guaranteed

- Bit-for-bit replay for flows that declare stochastic sources.
- Global determinism when any step opts into entropy.
- Replay acceptance without a policy that permits the observed variance.
