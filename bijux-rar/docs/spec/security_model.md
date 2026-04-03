
## Security Model
STATUS: AUTHORITATIVE

### Defended threats
- **Trace tampering:** Span+hash verification on evidence bytes; manifest hashing; fail-closed verifier.
- **Path traversal:** Symlink-safe resolution; relative POSIX paths enforced.
- **Replay integrity:** Corpus/index provenance pinned; mismatches fail.
- **API abuse:** API key + rate limiting; request/response size limits; denylisted content types.
- **Artifact pollution:** No root writes; artifacts confined to `artifacts/`.

### Not Defended (by design)
- **Untrusted plugins:** Only ReasonerBackend is supported; others are rejected.
- **Side-channel leaks:** Timing and resource exhaustion beyond quotas are not mitigated.
- **Host compromise:** Assumes runtime host is trusted.
- **LLM/model risks:** Non-deterministic backends are opt-in and not enabled in CI.

### Trust Boundaries
- Filesystem: only `artifacts/` is writable; evidence paths are validated.
- Network: runtimes are deterministic; external calls are treated as tools, recorded, and replayed from artifacts when frozen.
- API: authenticated via header; per-key rate limit; size limits enforced pre-handler.

### Replay as a Security Feature
- Replay validates that the same inputs/artifacts produce the same trace fingerprint, making tampering or drift detectable.

### Explicit Boundaries (merged from security boundaries)
- Defended: path traversal, trace/evidence tampering, replay drift, API abuse (token, rate limit, size, denylist).
- Not defended: host compromise, side channels, untrusted plugins beyond ReasonerBackend, non-deterministic LLM behavior (unless frozen/replayed).
- Trust assumptions: artifacts/ is the only writable root; ProblemSpecs are not sanitized beyond invariants; locale/time do not affect determinism.
- Undefined behavior: missing/altered artifacts; networked tools without recorded outputs for replay.

### What is NOT guaranteed
- No promise of confidentiality beyond documented denylists and quotas.
- No guarantee of availability under resource exhaustion or hostile clients.
- No support for arbitrary plugins/tools outside documented extension points.
- Backward compatibility beyond the stated versioning policy is not promised.

Scope Closure:
- Does NOT restate verifier policies; see [verification_model.md](verification_model.md).
- Does NOT define trace schema; see [trace_format.md](trace_format.md).
- Does NOT cover lifecycle states; see [trace_lifecycle.md](trace_lifecycle.md).

BREAKING_IF_CHANGED: true***
