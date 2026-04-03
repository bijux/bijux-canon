# Stability
> Stability boundaries for v1 users and integrators.

## Frozen in v1
- Public CLI commands: run, replay, inspect.
- API v1 schemas and required headers.
- Replay acceptability semantics and determinism classes.

## May change without notice
- Experimental CLI subcommands and output formatting.
- Internal storage layout and migration mechanics.
- Test fixtures and benchmarking thresholds.

## Requires major version bump
- Any change that alters replay equivalence outcomes.
- Breaking changes to public CLI or API fields.
- Contract semantics for failure taxonomy.
