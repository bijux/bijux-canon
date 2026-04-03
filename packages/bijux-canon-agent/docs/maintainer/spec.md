# Maintainer index

This section is for people changing the codebase and trying to keep the contract intact.

If you are a user of the CLI/API, you probably want `docs/user/usage.md` instead.

## Non-negotiables

- Preserve the **spec** (`docs/spec/*`) unless you intentionally version a breaking change.
- Preserve the architecture contract and package overview when the tree moves.
- Do not add hidden behavior (silent retries, implicit state, non-auditable side effects).

## Start here

1. `docs/maintainer/contributing.md`
2. `docs/project_overview.md`
3. `docs/maintainer/architecture_contract.md`
4. `docs/maintainer/tooling.md`
5. `docs/maintainer/testing.md`
