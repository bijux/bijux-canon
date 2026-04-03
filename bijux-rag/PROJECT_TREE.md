# Project Tree & Guide

Quick map of the bijux-rag repository (aligned with the bijux-cli documentation style).

## Top-Level Layout

```
.
├── .github/workflows/   # CI/CD (ci, deploy-docs, publish)
├── config/              # lint/type/security configs (coveragerc, mypy, pyright, pytype, ruff)
├── data/                # sample datasets (arxiv abstracts CSV)
├── docs/                # MkDocs sources (includes ADRs and reference pages)
├── makefiles/           # Makefile modules (api, build, citation, docs, hygiene, lint, publish, quality, sbom, security, test)
├── scripts/             # helper scripts (download_data, openapi_drift)
├── src/bijux_rag/       # library code (functional core + boundaries + effects)
├── tests/               # unit + e2e + strategies + eval assets
├── typings/             # custom stubs (msgpack)
├── .gitignore           # git ignores
├── CHANGELOG.md         # version history
├── CITATION.cff         # citation metadata
├── CODE_OF_CONDUCT.md   # community guidelines
├── CONTRIBUTING.md      # contributor guide
├── LICENSE              # MIT license
├── LICENSES/            # full texts (CC0-1.0, MIT)
├── Makefile             # main Makefile entrypoint
├── PROJECT_TREE.md      # this file
├── README.md            # project overview
├── REUSE.toml           # REUSE annotations
├── SECURITY.md          # security policy
├── TESTS.md             # tests overview
├── TOOLING.md           # tooling guide
├── USAGE.md             # usage instructions
├── mkdocs.yml           # MkDocs config
├── package.json         # Node deps (for Pyright)
├── pyproject.toml       # Hatchling build + deps
├── pytest.ini           # pytest config
├── tox.ini              # tox envs
└── artifacts/           # generated outputs (test coverage, lint reports, docs site, sbom, etc.)
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
- `docs/project_overview.md` — overview and tree (this content embedded via MkDocs).
- `docs/reference/` — API docs (cli.md, http_api.md, python.md via mkdocstrings).
- `docs/architecture/` — overview (index.md) + ADRs (adr/index.md).
- `docs/ADR/` — individual ADRs (0003-docstring-style, 0004-linting-quality, 0005-zero-pollution).
- `docs/artifacts.md` — artifact dir explanations.
- `docs/assets/` — images (bijux_icon/logo).
- `docs/community.md`, `docs/changelog.md`, `docs/tests.md`, `docs/tooling.md`, `docs/usage.md` — additional guides.

## Config & Tooling

- `pyproject.toml` — Hatchling build, deps, scripts, classifiers.
- `tox.ini` — multi-Python envs mirroring make targets.
- `pytest.ini` — pytest config (paths, markers, asyncio, timeouts).
- `mkdocs.yml` — MkDocs setup (theme, plugins, nav, extensions).
- `config/coveragerc.ini` — coverage omit/includes.
- `config/mypy.ini` — mypy strict settings.
- `config/pyrightconfig.json` — pyright includes/excludes.
- `config/pytype.cfg` — pytype inputs/excludes.
- `config/ruff.toml` — ruff line-length/target-version/selects.
- `Makefile` + `makefiles/` — entrypoints (`make test`, `make lint`, `make quality`, `make security`, `make api`, `make docs`, `make build`, `make sbom`, `make citation`, `make hygiene`, `make all`).
- `scripts/download_data.sh` — data fetcher.
- `scripts/openapi_drift.py` — API schema drift checker.

## Policies & Governance

- `CHANGELOG.md` — version history (Keep a Changelog format).
- `CITATION.cff` — citation metadata.
- `CODE_OF_CONDUCT.md` — Contributor Covenant.
- `CONTRIBUTING.md` — setup/workflow/PR guide.
- `SECURITY.md` — vulnerability reporting.
- `REUSE.toml` — license annotations (CC0 for assets, MIT for code/docs).
- `LICENSE`, `LICENSES/` — MIT + CC0 texts.

[Back to top](#project-tree--guide)
