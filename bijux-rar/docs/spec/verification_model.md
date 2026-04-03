
## Verifier Contract
Authoritative for: verifier guarantees and failure modes
Non-authoritative for: trace schema (see [trace_format.md](trace_format.md))
STATUS: AUTHORITATIVE  
[← Back to index](index.md)

### What Verification Means
- Ensures trace + plan obey schemas and invariants.
- Confirms every derived claim is grounded by verifiable citations (span+hash).
- Confirms tool linkage, evidence integrity, ordering, and required steps.
- Emits explicit failure reasons with severities.

### Hard Failure Triggers
- Missing or malformed events/fields.
- Citation marker missing or malformed.
- Span out of bounds or hash mismatch.
- Evidence file missing or hash mismatch.
- Tool call/result mismatch.
- Required steps absent.
- Plan/trace schema version mismatch.

### Insufficient Evidence
- If reasoning emits `InsufficientEvidenceOutput`, verification passes only when:
  - No derived claims are emitted, OR
  - All derived claims clearly marked insufficient (policy-driven).

### Not Promised
- No hallucination detection beyond span+hash grounding.
- No probabilistic guarantees.
- No acceptance of partial verification; failures are fail-closed.

**Next:** [failure_semantics.md](failure_semantics.md)  
**Previous:** [determinism.md](determinism.md)

### Outputs
- `VerificationReport` with `checks`, `failures`, `summary_metrics`.
- Failures are machine-actionable; no free-form prose is required for enforcement.

### Misuse Examples
- Treating verification as “answer correctness” → incorrect; verification enforces provenance and structure only.
- Skipping plan validation → rejected due to invariant failure.
- Omitting span+hash supports → derived claims are rejected.

### What Breaks if You Change This
- Relaxing span/hash checks makes claims unverifiable; auditability collapses.
- Soft-fail verification permits silent corruption; replay guarantees die.
- Removing tool linkage checks creates phantom tool calls/results; trace integrity fails.

### Non-Negotiable Invariants
- Verification is fail-closed on any invariant violation.
- Span+hash grounding is mandatory.
- Tool linkage and schema validation are mandatory.

Verifier Guarantees Matrix:
| Guarantee                | Enforced | Failure Mode   |
| ------------------------ | -------- | -------------- |
| Span hash integrity      | Yes      | Hard fail      |
| Event ordering           | Yes      | Reject trace   |
| Missing evidence         | Yes      | Invalid run    |
| Tool call/result linkage | Yes      | Invalid run    |
| Schema version support   | Yes      | Reject trace   |

Rejected Alternatives:
- Soft verification with warnings → rejected; enables drift and silent corruption.
- Accepting partial linkage → rejected; enables phantom tool calls.
- Ignoring span bounds → rejected; breaks grounding.

Scope Closure:
- Does NOT restate trace schema; see trace_format.md.
- Does NOT cover lifecycle states; see trace_lifecycle.md.
- Does NOT define replay semantics; see determinism.md.

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- Which failures cause verification to hard-fail.
- How insufficient evidence is treated.
- How schema/version and linkage violations are handled.***
