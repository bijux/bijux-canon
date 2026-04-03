# Invariants overview (one page)

```
Request
  | (contract + intent + budget validated)
  v
Session
  | (state machine; randomness + resources bound)
  v
Plan (fingerprinted)
  | (immutability enforced; capabilities checked)
  v
Execution
  | (algorithm + contract + randomness applied)
  v
Result + Provenance
  | (approximation + determinism reports; audit chain)
  v
Replay/Compare
  | (deterministic ⇒ equality; ND ⇒ envelope)
```

Invariants fire at every arrow:

- Contract/intent/budget required.
- Session transitions guarded.
- Plan fingerprint verified before execution.
- ND requires randomness profile and approximation report; deterministic forbids randomness.
- Provenance is mandatory; replay refuses without it.
