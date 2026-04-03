STATUS: EXPLANATORY

## Why This Is Hard

- Determinism is fragile: minor changes in ordering, hashing, or provenance break replay.
- Verification is expensive but necessary: soft checks invite drift and corruption.
- Shortcuts (e.g., skipping span+hash, loosening schemas) silently destroy auditability.
- Schema/version changes cascade: without migration, archives become unusable.
- Convenience features often undermine invariants; they are rejected by design.***
