STATUS: AUTHORITATIVE
# Trace Format (Authoritative Spec)
<a id="top"></a>
Authoritative for: trace schema, required fields, rejection rules
Non-authoritative for: execution flow, verification policies

### Versions
- `trace_schema_version`: integer, currently 1
- `fingerprint_algo`: `sha256`
- `canonicalization_version`: 1

### Event Types (exact list)
- `step_started` {step_id}
- `tool_called` {step_id, call}
- `tool_returned` {step_id, result}
- `evidence_registered` {step_id, evidence}
- `claim_emitted` {step_id, claim}
- `step_finished` {step_id, output}

### Required Fields
- Every event has `idx`, `kind`.
- `call.id` and `result.call_id` must match.
- `evidence` MUST include `id`, `uri`, `span`, `sha256`, `content_path`, `chunk_id`.
- `claim` MUST include `supports` with `span` and `snippet_sha256`.
- `output` is discriminated union (`understand`, `gather`, `derive`, `verify`, `finalize`, `insufficient`).

### Ordering
- Strictly increasing `idx`.
- Topological w.r.t. plan dependencies.

### Backward Compatibility
- New optional fields MAY be added with default behavior.
- Removing or renaming fields requires a schema-version bump and explicit upgrader.

### Rejection Rules
- Unknown event kinds.
- Missing required fields.
- Span outside evidence bytes.
- Hash mismatch between cited span and evidence.
- Mismatched `trace_schema_version`.

### Misuse Examples
- Adding custom event kinds → rejected as unknown schema.
- Omitting `chunk_id` or `content_path` in evidence → trace invalid.
- Using legacy markers without span+hash → derived claims rejected.

### What Breaks if You Change This
- Allowing unknown event kinds breaks replay and verifier expectations.
- Dropping span+hash or chunk_id makes evidence unverifiable; grounding collapses.
- Allowing unordered events invalidates dependency checks and replay determinism.

### Non-Negotiable Invariants
- Event kinds are closed and versioned.
- Span+hash + chunk_id are mandatory for evidence.
- Strict event ordering by `idx` is required.

### Trace as a Legal Object
- Valid trace: all required fields present; event kinds known; spans within evidence; hashes match; schema version supported.
- Invalid-but-parseable: JSONL can be read but invariants fail (e.g., span out of bounds, hash mismatch); verifier rejects.
- Rejected outright: unknown event kinds, missing mandatory fields, unsupported schema version; trace is not processed.

This contract is violated if:
- Any event deviates from the allowed kinds.
- Spans or hashes do not match evidence bytes.
- Schema version is not in the supported set.

Scope Closure:
- Does NOT cover lifecycle states (see [trace_lifecycle.md](trace_lifecycle.md)).
- Does NOT cover verifier policies (see [verification_model.md](verification_model.md)).
- Does NOT define replay semantics (see [trace_lifecycle.md](trace_lifecycle.md) / [determinism.md](determinism.md)).

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- What makes a trace valid vs invalid vs rejected outright.
- Which fields are mandatory for evidence and claims.
- Which schema versions are accepted and what happens otherwise.***

[Back to top](#top)
