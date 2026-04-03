STATUS: AUTHORITATIVE

## Doc → Code Map (Authority)

- `trace_format.md` → governs `src/bijux_rar/core/rar_types.py`, `boundaries/serde/trace_jsonl.py`, `rar/verification/checks.py` (schema fields, event validation). Doc supersedes code comments.
- `trace_lifecycle.md` → governs trace emission/consumption (`rar/execution/executor.py`, `rar/traces/replay.py`). Doc supersedes code comments for lifecycle state.
- `core_contracts.md` → governs system-wide invariants across execution/verification/replay. Doc supersedes code comments.
- `determinism.md` → governs deterministic behavior (`rar/retrieval/*`, `rar/execution/runtime.py`, `core/fingerprints.py`). Doc supersedes code comments.
- `verification_model.md` → governs verifier guarantees (`rar/verification/*`). Doc supersedes code comments.
- `security_model.md` → governs security posture (`security.py`, `httpapi.py`, path validation). Doc supersedes code comments.
- `versioning_compat.md` → governs schema/version compatibility logic. Doc supersedes code comments.

If code and these docs disagree, docs are authoritative and code must be fixed.***
