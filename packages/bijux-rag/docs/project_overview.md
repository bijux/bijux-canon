# Project Tree & Guide

Quick map of the bijux-rag package directory (aligned with the bijux-cli documentation style).

## Package Layout

```
.
├── ../../.github/workflows/ # repository-owned CI/CD workflows (bijux-rag-ci, bijux-rag-docs, bijux-rag-publish)
├── ../../configs/bijux-rag/ # root-managed lint/type/security configs
├── data/                # sample datasets (arxiv abstracts CSV)
├── docs/                # MkDocs sources (includes ADRs and reference pages)
├── ../../makes/bijux-rag/ # root-managed Make modules (api, build, docs, lint, publish, quality, sbom, security, test)
├── ../../scripts/bijux-rag/ # root-managed helper scripts (download_data, openapi_drift)
├── src/bijux_rag/       # library code (functional core + boundaries + effects)
├── tests/               # unit + e2e + strategies + eval assets
├── stubs/               # custom stubs (msgpack)
├── .gitignore           # git ignores
├── CHANGELOG.md         # version history
├── Makefile             # main Makefile entrypoint
├── README.md            # project overview
├── ../../configs/bijux-rag/mkdocs.yml # repo-owned MkDocs config
├── pyproject.toml       # Hatchling build + deps
├── ../../configs/pytest.ini # repo-wide pytest config
├── ../../tox.ini        # repository tox envs
└── ../../artifacts/bijux-rag/ # generated outputs (test coverage, lint reports, docs site, sbom, etc.)
```

## Source Code (high level)

- `src/bijux_rag/boundaries/` — shells and adapters (CLI via typer_cli/rag_main, HTTP via fastapi_app/rag_api_shell, exception_bridge, pydantic_edges, serde).
- `src/bijux_rag/core/` — shared RAG types (rag_types), structural dedup, rules (DSL/lint/pred).
- `src/bijux_rag/domain/` — effects and capabilities (async_ with concurrency/plan/resilience/stream, io_plan, io_retry, tx; facades, idempotent, logging, composition).
- `src/bijux_rag/fp/` — functional primitives (core with chunk/state_machine, effects like reader/state/writer, laws, applicative/functor/monoid/option_result/validation).
- `src/bijux_rag/infra/adapters/` — pluggable impls (async_runtime, atomic_storage, clock, file_storage, logger, memory_storage).
- `src/bijux_rag/interop/` — compat layers (dataframes, returns_compat, stdlib_fp, toolz_compat).
- `src/bijux_rag/pipelines/` — composable pipelines (cli, configured, distributed, specs).
- `src/bijux_rag/policies/` — reusable behaviors (breakers, memo, reports, resources, retries).
- `src/bijux_rag/rag/` — core RAG domain (app, chunking, clean_cfg/config, core, domain with chunk/embedding/metadata/perf/text, embedders, generators, indexes, ports, rag_api, rerankers, stages, stdlib_fp, streaming_rag, types).
- `src/bijux_rag/result/` — result monad (folds, stream, types).
- `src/bijux_rag/streaming/` — streaming utils (compose, contiguity, fanin/fanout, observability, sampling, time, types).
- `src/bijux_rag/tree/` — tree operations (_traversal, folds).

## Tests & Eval

- `tests/unit/` — focused units and property tests (boundaries/adapters, domain async/io/retry/session, fp laws/core/iter/pattern, infra adapters, interop, pipelines, policies, rag domain/api/stages, result option/folds/stream, streaming, tree flatten/folds).
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
- `../../configs/bijux-rag/mkdocs.yml` — repo-owned MkDocs setup (theme, plugins, nav, extensions).
- `../../configs/coveragerc.ini` — repo-wide coverage configuration.
- `../../configs/mypy.ini` — repo-wide mypy configuration.
- `../../configs/bijux-rag/package.json` — repo-owned Node manifest for OpenAPI tooling.
- `../../configs/bijux-rag/pytype.cfg` — pytype inputs/excludes.
- `../../configs/ruff.toml` — repo-wide Ruff configuration.
- `Makefile` + `../../makes/bijux-rag/` — entrypoints (`make test`, `make lint`, `make quality`, `make security`, `make api`, `make docs`, `make build`, `make sbom`, `make all`).
- `../../scripts/bijux-rag/download_data.sh` — data fetcher.
- `../../scripts/bijux-rag/openapi_drift.py` — API schema drift checker.

## Policies & Governance

- `CHANGELOG.md` — version history (Keep a Changelog format).
- `../../CODE_OF_CONDUCT.md` — repository-wide community standards.
- `docs/contributing.md` — package setup/workflow/PR guide.
- `../../SECURITY.md` — repository-wide vulnerability reporting.
- `../../LICENSE` — repository-wide MIT license text.

[Back to top](#project-tree--guide)
