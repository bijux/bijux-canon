
## Execution Flow (Single Pass)
STATUS: EXPLANATORY

Linear path, no branches:
`ProblemSpec → plan (Understand→Gather→Derive→Verify→Finalize) → trace.jsonl → verification → replay`

You understand this document if and only if you can answer:
- The single permitted execution cycle.
- Where trace is produced and consumed.
- Where mutation stops and replay begins.***

Step inputs/outputs:
- ProblemSpec in → Plan (DAG) out.
- Plan + runtime → Trace (ordered events) out.
- Trace + Plan → VerificationReport out.
- Trace + provenance → ReplayResult out.

Immutability points:
- Trace is mutable only while emitted; once written, any edit invalidates the run.
- Verification and replay read-only consume artifacts; no mutation allowed.

Undefined behavior:
- Any deviation from this flow (e.g., Derive before Gather) is rejected or invalidates the run.
