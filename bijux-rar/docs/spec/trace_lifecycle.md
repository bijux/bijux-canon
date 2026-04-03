
## Trace Lifecycle (State Machine)
Authoritative for: lifecycle states of trace artifacts
Non-authoritative for: trace schema fields
STATUS: AUTHORITATIVE  
[← Back to index](index.md)

States:
- **Creating**: events appended in order during execution.
- **Sealed**: trace.jsonl written; manifest hashes recorded.
- **Verified**: verification report produced; no mutation allowed.
- **Replayed**: replay result computed; relies on sealed artifacts.

Transitions:
- Creating → Sealed when execution completes writing trace and manifest.
- Sealed → Verified when verifier runs; any mismatch = rejection.
- Sealed/Verified → Replayed when replay runs; fingerprint drift = failure.

Invalidation:
- Any edit to trace or evidence after sealing invalidates the run.
- Missing artifacts or schema-version mismatch causes rejection before verify/replay.

Undefined behavior:
- Appending events after sealing.
- Reordering events.
- Running verify/replay with partial artifacts.

Non-Negotiable Invariants:
- Trace is immutable after sealing.
- Manifest hashes bind evidence to the trace.
- Replay consumes sealed artifacts only.

Scope Closure:
- Does NOT restate trace schema; see [trace_format.md](trace_format.md).
- Does NOT define verifier policies; see [verification_model.md](verification_model.md).

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- When a trace is mutable vs sealed.
- What invalidates a sealed trace.

**Next:** [core_contracts.md](core_contracts.md)  
**Previous:** [trace_format.md](trace_format.md)
- How replay interacts with sealed artifacts.***
