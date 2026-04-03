
## State vs Artifacts vs Derivations
STATUS: EXPLANATORY

Runtime State:
- Lives in process memory (planner, executor, runtime buckets).
- Mutable during execution only.
- Discarded after run; not relied on for replay.

Persistent Artifacts:
- Stored under `artifacts/runs/<run_id>/`.
- Immutable after creation; mutation invalidates run.
- Includes corpus snapshot, index, trace, manifest, provenance, verification.

Derived Values:
- Calculated from artifacts (fingerprints, metrics, replay results).
- Must be reproducible from artifacts alone.
- Not stored as authoritative sources; artifacts are.

Replay expectations:
- Only artifacts are trusted inputs to replay.
- Runtime state is recreated; derivations must match or replay fails.

Undefined behavior:
- Using any external state or missing artifacts during replay.

You understand this document if and only if you can answer:
- Which data is runtime state vs artifact vs derivation.
- Which parts are mutable and when.
- What replay is allowed to consume.***
