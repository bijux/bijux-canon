STATUS: AUTHORITATIVE

## Doc → Code Map (Authority)

- `trace_format.md` → governs `src/bijux_canon_reason/core/types.py`, `interfaces/serialization/trace_jsonl.py`, `verification/checks.py` (schema fields, event validation). Doc supersedes code comments.
- `trace_lifecycle.md` → governs trace emission/consumption (`execution/executor.py`, `traces/replay.py`). Doc supersedes code comments for lifecycle state.
- `core_contracts.md` → governs system-wide invariants across execution/verification/replay. Doc supersedes code comments.
- `determinism.md` → governs deterministic behavior (`retrieval/*`, `execution/runtime.py`, `core/fingerprints.py`). Doc supersedes code comments.
- `verification_model.md` → governs verifier guarantees (`verification/*`). Doc supersedes code comments.
- `security_model.md` → governs security posture (`interfaces/security.py`, `api/v1/app.py`, path validation). Doc supersedes code comments.
- `versioning_compat.md` → governs schema/version compatibility logic. Doc supersedes code comments.

If code and these docs disagree, docs are authoritative and code must be fixed.***
