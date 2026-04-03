
## Versioning & Compatibility
STATUS: AUTHORITATIVE

Breaking change definition:
- Any schema field removal/rename.
- Any invariant relaxation/tightening.
- Any change to fingerprint canonicalization or hashing.

Trace compatibility:
- Supported `trace_schema_version` set is fixed in code.
- Unknown versions are rejected unless an explicit upgrader is provided.
- Older traces must be upgraded via documented migrators; otherwise rejected.

Artifact longevity:
- Artifacts are intended to be archivable; replay must succeed with pinned corpus/index/provenance and matching schema versions.
- Changing canonicalization_version or fingerprint_algo breaks compatibility; requires major release and migrator.

Undefined behavior:
- Consuming traces/artifacts with mismatched versions without migration.

Compatibility Promise Table:
| Aspect                    | Never changes without major bump | May change with migration | May change anytime |
| ------------------------- | -------------------------------- | ------------------------- | ------------------ |
| Trace schema version set  | Yes                              | With explicit migrator    | No                 |
| Fingerprint algorithm     | Yes                              | No                        | No                 |
| Canonicalization version  | Yes                              | With explicit migrator    | No                 |
| Optional fields (additive)| No                               | Yes                       | No                 |
| Invariants                | Yes                              | With major bump           | No                 |

Scope Closure:
- Does NOT restate trace schema; see [trace_format.md](trace_format.md).
- Does NOT define verifier behavior; see [verification_model.md](verification_model.md).
- Does NOT define lifecycle; see [trace_lifecycle.md](trace_lifecycle.md).

BREAKING_IF_CHANGED: true

You understand this document if and only if you can answer:
- What constitutes a breaking change.
- How older traces are treated when schema versions differ.
- Which aspects can change with/without migration.***
