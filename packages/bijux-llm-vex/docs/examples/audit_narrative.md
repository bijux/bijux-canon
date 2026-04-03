# Audit narrative (truth trace)

Flow:
```
request (contract + intent + budget)
  → session (state machine binds randomness + resources)
  → plan (fingerprinted, capability-checked)
  → execution (algorithm + contract + randomness applied)
  → result (deterministic/ND + ApproximationReport + DeterminismReport)
  → audit (ledger + chain hash)
  → replay/compare (deterministic ⇒ equality, ND ⇒ envelope) or refusal
```

Key checkpoints:

- Contract/intent validated up front; ND without ANN raises `NDExecutionUnavailableError`.
- Plan immutability enforced before execution (fingerprint check).
- Provenance persisted with approximation + randomness metadata.
- Replay refuses without provenance; compare requires matching provenance lineage.
