Owner: Bijan Mousavi <bijan@bijux.io>
Status: stable
Scope: Contributing to bijux-canon-agent.

# Contributing to bijux-canon-agent

Keep the process boring and predictable.

## Ground rules
- Determinism and provenance are non-negotiable; never weaken invariants.
- All changes must pass `make lint quality security test`.
- Public surfaces (`cli`, core pipeline stages, trace schema) require tests and doc updates.
- Do not merge with a dirty worktree or failing CI.

## Workflow
1. Fork/branch from `main`.
2. Implement code, tests, and docs together.
3. Run the full gate: `make lint quality security test`.
4. Open a PR with a concise description and link to relevant docs/specs.

## Commit/tag hygiene
- Versions are derived from git tags via `hatch-vcs`; never hard-code.
- Breaking changes require explicit ABI/public API version bumps and doc updates.
- Licensing: repository content is Apache License 2.0; see `LICENSE`.

## Questions
File an issue or start a discussion on GitHub. Be explicit about contracts and invariants you’re touching.
