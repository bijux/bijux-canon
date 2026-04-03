STATUS: AUTHORITATIVE

## Forbidden Changes

- Changing event kinds or schemas without version bump + migrator.
- Allowing writes outside `artifacts/runs/<run_id>/`.
- Relaxing span+hash grounding or citation markers.
- Introducing non-deterministic behavior into replay or verification.
- Removing or altering invariant IDs without coordination.
- Never weakening determinism, replay, or verification guarantees for convenience.
- Breaking changes without version bump, migration plan, and doc update are rejected.
- Refactoring away manifest/provenance hashing or sealed trace semantics.***
