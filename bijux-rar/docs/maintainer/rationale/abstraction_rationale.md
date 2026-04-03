
## Abstraction Rationale
STATUS: EXPLANATORY

Planner:
- Rejected simpler “inline steps” because explicit plan DAG enables validation and replay ordering. Without it, dependency errors go undetected.

Verifier:
- Rejected “best-effort” checks because fail-closed is required for auditability. Soft verification would allow silent corruption.

FrozenRuntime:
- Rejected “re-run tools live” for replay because determinism requires pinned outputs/config. Live replay would allow drift and tampering.

ReasonerBackend:
- Rejected ad-hoc reasoning code paths; a single extension seam keeps claims/citations verifiable and prevents arbitrary logic from bypassing grounding.
