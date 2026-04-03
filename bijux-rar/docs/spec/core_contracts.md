
STATUS: AUTHORITATIVE

## Core Contract (Immutable, Normative)
<a id="top"></a>
Authoritative for: system-wide contracts and invariants
Non-authoritative for: trace schema details (see [trace_format.md](trace_format.md))
STATUS: AUTHORITATIVE

Rules (numbered, MUST/SHALL only):
1. A run MUST emit `trace.jsonl` with strictly increasing `idx`; any rewrite or reorder invalidates the run.
2. Every derived claim MUST cite evidence using `[evidence:<id>:<b0>-<b1>:<sha256>]` computed over exact evidence bytes; missing/mismatched hashes SHALL be rejected.
3. Replay MUST reproduce fingerprints when corpus/index/provenance match; fingerprint drift SHALL fail the run.
4. All artifacts SHALL live under `artifacts/runs/<run_id>/`; writes elsewhere are forbidden.
5. Trace/plan/manifest MUST carry supported schema versions; unknown versions SHALL be rejected unless an explicit upgrader exists.
6. Any invariant violation (span bounds, missing evidence, unknown tool, hash mismatch) SHALL hard-fail verification; no soft modes exist.

Out of Scope (non-goals, binding):
- Best-effort verification is not provided.
- Legacy citation markers (`[evidence:X]`) are not accepted.
- Implicit network/LLM calls during replay are not allowed.
- Wall-clock time or locale SHALL NOT influence determinism.

Breaking Changes Policy:
- Minor releases MAY add backward-compatible fields.
- Major releases MAY change schemas or invariants; such changes REQUIRE a migrator or explicit rejection path.

Misuse Examples:
- Citing whole documents instead of chunks → rejected for missing chunk alignment.
- Editing evidence after manifest generation → hash mismatch triggers hard failure.
- Injecting extra events into `trace.jsonl` → schema/invariant validation rejects the run.

What Breaks if You Change This:
- Relaxing span+hash grounding destroys replay/verifier integrity.
- Allowing root writes pollutes the audit trail; artifacts become untrusted.
- Accepting legacy markers reintroduces unverifiable claims; grounding collapses.

Non-Negotiable Invariants:
- Trace immutability is enforced; edits invalidate runs.
- Span+hash grounding is mandatory for derived claims.
- Artifacts must live under `artifacts/runs/<run_id>/`.
- Only supported schema versions are accepted; unknown versions are rejected.

Rejected Alternatives:
- Allowing best-effort verification → rejected because it permits silent corruption and breaks auditability.
- Accepting legacy markers → rejected because citations become unverifiable.
- Allowing writes outside artifacts/ → rejected because provenance and determinism would be unenforceable.

Scope Closure:
- Does NOT restate trace schema; see trace_format.md.
- Does NOT define lifecycle states; see trace_lifecycle.md.
- Does NOT define verifier policies; see verification_model.md.

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- Which behaviors invalidate a run immediately.
- Where artifacts must live and why.
- How schema version mismatches are handled.***

[Back to top](#top)
