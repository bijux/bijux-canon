
## Maintenance & Extension Guide
STATUS: EXPLANATORY

Allowed:
- Extend `ReasonerBackend` with deterministic outputs and verifiable citations.
- Add new verification checks if they remain fail-closed and schema-aware.
- Add metrics/eval outputs that derive from existing artifacts.

Forbidden:
- New event kinds without schema/version bump.
- New write locations outside `artifacts/runs/<run_id>/`.
- Relaxing grounding or replay invariants.
- Adding runtime globals or hidden state.

How to extend safely:
- Preserve schemas and invariants; if a change is breaking, bump versions and provide migrators.
- Keep replay deterministic; any new runtime behavior must be recordable and replayable.
- Add tests that fail on invariant violations and mismatched fingerprints.
