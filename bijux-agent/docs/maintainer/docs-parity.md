# Docs ↔ code parity

Docs are treated as part of the contract.

## What “parity” means

- The spec must not describe behavior the code does not implement.
- The code must not implement behavior the spec forbids or fails to mention (when contract-relevant).
- Where drift is unavoidable (e.g. planned endpoints), drift must be called out explicitly.

## Practical rule

If you change runtime behavior or artifact structure:

1. Update the relevant `docs/spec/*` page.
2. Regenerate documentation checksums (`docs/doc_checksums.json`).
3. Keep `docs/index.md` file list in sync.

See: `docs/maintainer/documentation-invariant.md`.
