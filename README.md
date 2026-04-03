# bijux-llm-nexus

Unified repository for Bijux LLM packages and applications.

Python distributions live under `packages/`, while shared repository assets stay
at the root. This keeps each package independently publishable, preserves the
standard per-package `src/` layout, and avoids the ambiguity of a single
repo-wide `src/` tree.

Projects:

- `packages/bijux-llm-flows`
- `packages/bijux-llm-agent`
- `packages/bijux-llm-rag`
- `packages/bijux-llm-rar`
- `packages/bijux-llm-vex`

Shared repository assets:

- `configs/` for root-managed tooling configuration
- `Makefile` for root package orchestration
- `makes/` for root-managed build and quality targets
- `LICENSE` for the repository-wide MIT license
- `mkdocs.yml` for the repository handbook
- `packages/` for publishable Python distributions
- `pyproject.toml` for repository tooling metadata
- `tox.ini` for root validation environments

History preservation details are documented in `docs/repository-history.md`.
Repository handbook pages live under `docs/`.
