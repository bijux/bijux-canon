
## Extension Points (Only One)
STATUS: EXPLANATORY

Supported seam: **ReasonerBackend**

### How to implement
- Implement `ReasonerBackend` interface in `src/bijux_rar/rar/reasoning/backend.py`.
- Produce `Derivation` objects with verifiable `citations` (span+hash).
- Register backend via configuration/preset, not globals.

### Everything else is closed
- No custom event types.
- No custom verification rules.
- No custom storage backends for core artifacts.
- No tool protocol changes.

Rationale: limiting extension to reasoning keeps artifacts, verification, and replay stable.***
