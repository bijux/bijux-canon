
## System Contract (One Page, Normative)
<a id="top"></a>
STATUS: AUTHORITATIVE  
[← Back to index](index.md)

- Determinism: fingerprints, chunking, plan execution, and replay are deterministic given pinned corpus/index/provenance; drift fails the run.
- Evidence: all claims MUST cite evidence via span+hash markers; hashes computed over evidence bytes; mismatches are hard failures.
- Replay: consumes sealed artifacts only; provenance hashes must match; any drift or missing artifact refuses replay.
- Verification: fail-closed; schema/version mismatches, linkage failures, or hash/spans mismatches invalidate the run.
- Failure: any invariant violation invalidates the run; no soft modes.

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- How determinism, evidence grounding, replay, and verification interact.
- What happens on any invariant violation.
- What artifacts are mandatory for a valid run.***

## What is NOT guaranteed
- Performance characteristics beyond documented benchmarks.
- Backward compatibility with trace/schema versions before v0.1.0.
- Acceptance of partially-grounded claims or probabilistic outputs.
- Support for unpinned or external artifacts during replay.

**Next:** [versioning_compat.md](versioning_compat.md)  
**Previous:** [core_contracts.md](core_contracts.md)

[Back to top](#top)
