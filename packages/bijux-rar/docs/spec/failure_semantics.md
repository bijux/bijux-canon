
## Failure Semantics
STATUS: AUTHORITATIVE

Classes:
- **Validation failures**: schema or invariant errors → fatal, user error.
- **Verification failures**: span/hash mismatch, linkage errors → fatal, user error.
- **Replay failures**: fingerprint drift, provenance mismatch → fatal, system integrity check.
- **IO failures**: missing files, permission errors → fatal until resolved.
- **Misuse**: forbidden flow, root pollution, unpinned corpus → fatal; run invalidated.

Recoverable vs fatal:
- Any failure above is fatal for the run; restart with corrected inputs/artifacts.

Undefined behavior:
- Ignoring failures or forcing continuation; system makes no guarantees.

Scope Closure:
- Does NOT restate trace schema; see [trace_format.md](trace_format.md).
- Does NOT cover verifier policies; see [verification_model.md](verification_model.md).

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- Which failures are fatal vs out of scope.
- How misuse is classified.
- Why no failure is recoverable without rerun.***
