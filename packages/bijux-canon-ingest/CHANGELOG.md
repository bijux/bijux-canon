# Changelog

All notable changes to `bijux-canon-ingest` are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release, including legacy distribution naming where applicable.

## 0.3.6 - 2026-04-20

### Changed

- Prepared the `v0.3.6` release line by aligning fallback versions and inter-package dependency floors across the repository.
- Synchronized release automation and governance with the `bijux-std v0.1.3` shared standards baseline.

### Fixed

- `release-pypi.yml` now uses parse-safe publication gating for token/bootstrap checks.
- Protected workflow policy checks now accept shared-manifest-driven standards updates through approved control paths.

## [0.3.5] - 2026-04-19

### Changed

- Package contract docs now reference canonical schema paths under
  `apis/bijux-canon-ingest/v1`.
- Shared handbook links now resolve canonical package handbook routes for
  ingest documentation and migration surfaces.

## [0.3.4] - 2026-04-11

### Fixed

- Release fallback metadata and source-checkout version fallback now align with
  the synchronized `v0.3.4` tag.
- Package README badge links now follow the shared badge catalog and point to
  the exact GHCR package pages used for published ingest bundles.

## [0.3.2] - 2026-04-10

### Fixed

- Release fallback metadata and source-checkout version fallback now align with
  the `v0.3.2` tag.

## [0.3.0] - 2026-04-05

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
- PyPI metadata, search keywords, and project URLs now make the canonical
  ingest package easier to discover from package indexes and Bijux-owned docs.
- The package README now uses PyPI-safe badge and link targets, and it points
  legacy `bijux-rag` users to the canonical migration path and retired
  repository guidance.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so ingest release expectations stay attached to the
  package.
- Build-time version metadata now writes to a generated module so packaging
  commands stop dirtying the tracked source tree.

### Fixed

- Root package checks, package-local typing configuration, and fallback version
  behavior were aligned for the current `0.3.0` line.
- CLI boundary wiring, HTTP request mapping, UTC clock adapter behavior, and
  source-tree cache hygiene were tightened during the refactor series.
- Release artifacts now ship the repository `LICENSE` file so downstream
  consumers receive the license text with the published package.
- HTTP app tests now assert the canonical OpenAPI title string that matches the
  checked-in v1 contract artifacts.

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
