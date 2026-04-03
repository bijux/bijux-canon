# Design diary (traceability)

This diary records design pressures, reversals, and lessons learned. Update it only when something hurts.

- ANN integration: kept a single reference runner to avoid taxonomy sprawl; randomness surfaces must be explicit and audited.
- Replay semantics: deterministic is replayable; ND is envelope-validated only. Storing `replayable` was removed to prevent drift.
- Capability honesty: backends must declare `supports_ann`; dishonesty now fails fast with structured errors.
- Retention limits: ledgers enforce artifact/result caps to avoid slow operational leaks.

When making changes, add a short bullet describing the pressure and the chosen trade-off.
