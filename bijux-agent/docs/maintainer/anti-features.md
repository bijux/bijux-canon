# Anti-features (maintainer)

Anti-features are explicit “no” decisions that prevent scope creep.

- No stateful cross-run memory by default.
- No dynamic pipeline graphs at runtime.
- No silent retries unless driven by an explicit policy.
- No “magic” behavior that bypasses trace recording.
- No claiming replayability when sampling is enabled.

If you want to add an exception, write it down, version it, and update the spec.
