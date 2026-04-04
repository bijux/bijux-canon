# bijux-canon

Unified repository for the Bijux Canon package family.

Python distributions live under `packages/`, while the repository root keeps
only the assets that genuinely need to sit above one package: shared schemas,
workspace automation, contributor rules, and the root handbook.

Projects:

- `packages/bijux-canon-runtime`
- `packages/bijux-canon-agent`
- `packages/bijux-canon-ingest`
- `packages/bijux-canon-reason`
- `packages/bijux-canon-index`

Shared repository assets:

- `apis/` for shared schema sources and pinned artifacts
- `configs/` for root-managed tooling configuration
- `docs/` for the hand-authored repository handbook
- `Makefile` and `makes/` for workspace automation
- `packages/` for publishable Python distributions
- `pyproject.toml` for repository tooling metadata
- `tox.ini` for root validation environments

Repository-owned developer tooling, including docs-side utilities that do not
belong at the root, lives in `packages/bijux-canon-dev`.

History preservation details are documented in `docs/repository-history.md`.
