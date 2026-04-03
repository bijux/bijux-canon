# Project Tree & Guide

Quick map of the bijux-rag package directory (aligned with the bijux-cli documentation style).

## Package Layout

```
.
├── ../../.github/workflows/ # repository-owned CI/CD workflows (ci-bijux-canon-ingest, docs-bijux-canon-ingest, publish-bijux-canon-ingest)
├── ../../configs/bijux-rag/ # root-managed lint/type/security configs
├── data/                # sample datasets (arxiv abstracts CSV)
├── docs/                # MkDocs sources (includes ADRs and reference pages)
├── ../../makes/bijux-rag/ # root-managed Make modules (api, build, docs, lint, publish, quality, sbom, security, test)
├── ../../scripts/bijux-canon-ingest/ # root-managed helper scripts (download_data, openapi_drift)
├── src/bijux_rag/       # library code (functional core + transports + effects)
├── tests/               # unit + e2e + strategies + eval assets
├── stubs/               # custom stubs (msgpack)
├── .gitignore           # git ignores
├── CHANGELOG.md         # version history
├── Makefile             # main Makefile entrypoint
├── docs/index.md        # project overview
├── ../mkdocs.yml        # package-owned MkDocs config
├── pyproject.toml       # Hatchling build + deps
├── ../../configs/pytest.ini # repo-wide pytest config
├── ../../tox.ini        # repository tox envs
└── ../../artifacts/bijux-canon-ingest/ # generated outputs (test coverage, lint reports, docs site, sbom, etc.)
```

## Source Code (high level)

- `src/bijux_rag/http/` — FastAPI transport entrypoint.
- `src/bijux_rag/boundaries/` — boundary exception helpers.
- `src/bijux_rag/serde/` — JSON/MessagePack codecs and Pydantic edge models.
- `src/bijux_rag/cli/` — CLI entrypoints and file-oriented command helpers (`entrypoint`, `pipeline_runner`, `file_api`, `file_pipeline`, `typer_app`).
- `src/bijux_rag/application/` — orchestration layer (`pipelines`, `api`, `observability`, `rag`).
- `src/bijux_rag/config/` — package configuration models.
- `src/bijux_rag/config/` — package and pipeline configuration models (`AppConfig`, `RagConfig`, `CleanConfig`).
- `src/bijux_rag/core/` — shared RAG types (rag_types), structural dedup, rules (DSL/lint/pred).
- `src/bijux_rag/processing/` — pure pipeline transforms (`chunking`, `stages`, `streaming`, `stdlib`).
- `src/bijux_rag/retrieval/` — retrieval backends and domain types (`domain`, `embedders`, `generators`, `indexes`, `ports`, `rerankers`).
- `src/bijux_rag/domain/` — effects and capabilities (async_ with concurrency/plan/resilience/stream, io_plan, io_retry, tx; facades, idempotent, logging, composition).
- `src/bijux_rag/fp/` — functional primitives (core with chunk/state_machine, effects like reader/state/writer, laws, applicative/functor/monoid/option_result/validation).
- `src/bijux_rag/infra/adapters/` — pluggable impls (async_runtime, atomic_storage, clock, file_storage, logger, memory_storage).
- `src/bijux_rag/interop/` — compat layers (dataframes, returns_compat, stdlib_fp, toolz_compat).
- `src/bijux_rag/policies/` — reusable behaviors (breakers, memo, reports, resources, retries).
- `src/bijux_rag/result/` — result monad (folds, stream, types).
- `src/bijux_rag/streaming/` — streaming utils (compose, contiguity, fanin/fanout, observability, sampling, time, types).
- `src/bijux_rag/tree/` — tree operations (_traversal, folds).

## Tests & Eval

- `tests/unit/` — focused units and property tests (application, boundaries, processing, retrieval, serde, domain async/io/retry/session, fp laws/core/iter/pattern, infra adapters, interop, policies, result option/folds/stream, streaming, tree flatten/folds).
- `tests/e2e/` — end-to-end smoke/gates (cli_smoke, eval_suite, rag_truthfulness_gate, real_rag_smoke) with fixtures.
- `tests/eval/` — pinned corpus/queries JSONL with licenses.
- `tests/strategies.py` — Hypothesis strategies for trees/chains/results.
- `tests/helpers.py` — test utils.
- `tests/conftest.py` — global fixtures.

## Docs

- `docs/index.md` — front door (embeds README).
- `docs/project_overview.md` — overview and tree (this page).
- `docs/reference/` — API docs (cli.md, http_api.md, python.md via mkdocstrings).
- `docs/architecture/` — overview (index.md) + ADRs (adr/index.md).
- `docs/ADR/` — individual ADRs (0003-docstring-style, 0004-linting-quality, 0005-zero-pollution).
- `docs/artifacts.md` — artifact dir explanations.
- `../../docs/assets/` — shared documentation images and styles.
- `docs/changelog.md` — changelog page backed by the package changelog.
- `docs/community.md` — community expectations and repo-wide conduct links.
- `docs/contributing.md` — package contribution workflow.
- `docs/tests.md` — testing guide.
- `docs/tooling.md` — tooling guide.
- `docs/usage.md` — usage instructions.

## Config & Tooling

- `pyproject.toml` — Hatchling build, deps, scripts, classifiers.
- `../../tox.ini` — repository tox envs mirroring package make targets.
- `../../configs/pytest.ini` — repo-wide pytest config.
- `../mkdocs.yml` — package-owned MkDocs setup (theme, plugins, nav, extensions).
- `../../configs/coveragerc.ini` — repo-wide coverage configuration.
- `../../configs/mypy.ini` — repo-wide mypy configuration.
- `../../configs/package.json` — repo-wide Node manifest for OpenAPI tooling.
- `../../configs/ruff.toml` — repo-wide Ruff configuration.
- `Makefile` + `../../makes/bijux-rag/` — entrypoints (`make test`, `make lint`, `make quality`, `make security`, `make api`, `make docs`, `make build`, `make sbom`, `make all`).
- `../../scripts/bijux-canon-ingest/download_data.sh` — data fetcher.
- `../../scripts/bijux-canon-ingest/openapi_drift.py` — API schema drift checker.

## Policies & Governance

- `CHANGELOG.md` — version history (Keep a Changelog format).
- `../../CODE_OF_CONDUCT.md` — repository-wide community standards.
- `docs/contributing.md` — package setup/workflow/PR guide.
- `../../SECURITY.md` — repository-wide vulnerability reporting.
- `../../LICENSE` — repository-wide Apache 2.0 license text.

[Back to top](#project-tree--guide)
