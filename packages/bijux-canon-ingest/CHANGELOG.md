# Changelog

All notable changes to `bijux-canon-ingest` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release, including legacy distribution naming where applicable.

## [Unreleased]

- PyPI metadata, search keywords, and project URLs now make the canonical
  ingest package easier to discover from package indexes and Bijux-owned docs.
- The package README now uses PyPI-safe badge and link targets, and it points
  legacy `bijux-rag` users to the canonical migration path and retired
  repository guidance.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so ingest release expectations stay attached to the
  package.

## [0.3.0] - 2026-04-04

### Added

- Package-local documentation now explains ingest ownership, layout,
  architecture, and test strategy in clearer maintainers-first language.
- Package layout and docs integrity checks were added to keep source structure
  and package guides aligned.
- Stable optional Typer command wiring and package version publication were
  added to the package-facing boundaries.

### Changed

- The package was realigned under the canonical `bijux-canon-ingest` identity,
  with source packages and docs renamed away from legacy `rag` terminology.
- Ingest workflows were reorganized around clearer `application/`, `config/`,
  `interfaces/`, `processing/`, `retrieval/`, `observability/`, and
  `integrations/` ownership.
- CLI, HTTP, retrieval, and document I/O paths were split into smaller modules
  so deterministic ingest behavior is easier to follow and maintain.
- Domain and adapter boundaries were tightened around embedder selection,
  serialization envelopes, stored-index access, observability payloads, and
  shell-backed document I/O.

### Fixed

- Root package checks, package-local typing configuration, and fallback version
  behavior were aligned for the current `0.3.0` line.
- CLI boundary wiring, HTTP request mapping, UTC clock adapter behavior, and
  source-tree cache hygiene were tightened during the refactor series.

## [0.1.0] – 2025-12-26

### Added

- **Core and Functional Primitives**: Added RAG types (`RawDoc`, `Chunk`), result monad (`Result[T, ErrInfo]` with monadic operations and folds like `fold_results_fail_fast`), immutable document trees via `make_chunk`, and tree utilities (`flatten`, `fold_tree`) with stack-safety.
- **Effect Descriptions**: Introduced `IOPlan` for deferred sync I/O (`io_pure`, `io_bind`, `perform`), retry wrappers (`retry_idempotent` with `RetryPolicy`), and transaction bracketing (`Session`, `Tx`, `with_tx`).
- **Async Effects and Streams**: Defined `AsyncPlan`/`AsyncGen` for async operations (`async_pure`, `async_bind`, `async_gather`, `async_gen_map`, `async_gen_flat_map`, `async_gen_gather`), with lifts for sync integration (`lift_sync`, `lift_sync_with_executor`).
- **Resilience and Policies**: Added async policies for retries (`AsyncRetryPolicy`), timeouts (`TimeoutPolicy`), backpressure (`BackpressurePolicy`), rate limiting (`RateLimitPolicy`), fairness (`FairnessPolicy`), and chunking (`ChunkPolicy`); included test fakes (`FakeClock`, `FakeSleeper`, `ResilienceEnv`).
- **Streaming Combinators**: Provided bounded mapping (`async_gen_bounded_map`), rate limiting (`async_gen_rate_limited`), fair merging (`async_gen_fair_merge`), and chunking (`async_gen_chunk`); added streaming maps (`try_map_iter`, `par_try_map_iter`).
- **Interop and Helpers**: Included stdlib FP utilities (`merge_streams`, `running_sum`) and Toolz-compatible functions (`compose`, `curried_map`, `reduceby`); added chunking policies (`fixed_size_chunk`).
- **Adapters and Pipelines**: Implemented storage adapters (`FileStorage`, `InMemoryStorage`) with CSV support; defined composable pipelines like `embed_docs`.
- **Boundaries and APIs**: Added CLI entrypoint (`bijux-rag`) for processing/serving; FastAPI HTTP API with embedding/retrieval endpoints and OpenAPI schema.
- **Typing and Testing**: Included `py.typed` markers, msgpack stubs, and strict configs for MyPy/Pyright/Pytype; comprehensive tests with Hypothesis (laws, equivalence), coverage, and E2E markers.
- **Documentation and Tooling**: MkDocs setup with Material theme, plugins (mkdocstrings, minify), and pages for overview, usage, API reference, architecture (ADRs), and changelog.
- **Quality Pipeline**: Linting (Ruff), code health (Vulture, Deptry, Interrogate), security (Bandit, Pip-Audit), modular Makefiles (test, lint, docs, build), Tox envs (3.11-3.13), and CI with GitHub Actions.
- **Build and Compliance**: Hatchling packaging with VCS versioning; SBOM (CycloneDX), citations (CFF, BibTeX); REUSE compliance with MIT/CC0 licenses.

[Back to top](#top)
