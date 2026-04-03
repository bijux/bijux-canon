# Maintainer index

This section is for people changing the codebase and trying to keep the contract intact.

If you are a user of the CLI/API, you probably want `docs/user/usage.md` instead.

## Non-negotiables

- Preserve the **spec** (`docs/spec/*`) unless you intentionally version a breaking change.
- Preserve the documentation checksum invariant (`docs/doc_checksums.json` + `docs/index.md` list).
- Do not add hidden behavior (silent retries, implicit state, non-auditable side effects).

## Start here

1. `docs/maintainer/contributing.md`
2. `docs/maintainer/tooling.md`
3. `docs/maintainer/testing.md`
4. `docs/maintainer/code-map.md`
5. `docs/maintainer/documentation-invariant.md`
