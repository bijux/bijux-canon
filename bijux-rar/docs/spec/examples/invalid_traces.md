
STATUS: EXPLANATORY
## Invalid Trace Examples (Misuse)

- **Tampered hash**: evidence bytes changed after manifest → span hash mismatch → verifier fails `check_support_spans`.
- **Missing step**: Derive emitted without Gather → dependency violated → trace rejected by invariants.
- **Replay with wrong corpus**: provenance hash mismatch → replay refuses to run.
- **Version mismatch**: `trace_schema_version` not supported → trace rejected outright.

These are intentionally hostile cases; any acceptance is a bug.***
