# Pipeline refactor rules (maintainer)

These rules exist to prevent “refactor” from becoming “behavior drift”.

## Rules

- Do not change canonical phase order casually.
- Any change to allowed transitions requires:
  - explicit rationale,
  - updated spec text,
  - versioning decision.
- Preserve trace writing semantics; do not introduce execution paths that bypass trace recording.
- When adding new trace fields, keep them forward-compatible (consumers ignore unknown fields).

## Minimal acceptance criteria

- unit tests pass
- documentation invariant tests pass
- trace validation succeeds for a normal run
