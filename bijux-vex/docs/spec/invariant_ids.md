# Invariant IDs

Every invariant failure **MUST** emit an ID. Defaults use `INV-000` but should be replaced with specific IDs over time.

- INV-000: unspecified invariant violation (temporary default)
- INV-010: execution contract mismatch
- INV-011: backend capability refusal
- INV-020: missing randomness for ND execution
- INV-021: budget exhaustion triggered
- INV-030: plan fingerprint mismatch
- INV-040: deterministic replay divergence

Each ID **MUST** appear in exception text and **MUST** be covered by at least one test.
