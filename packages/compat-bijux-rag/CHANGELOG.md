# Changelog

All notable changes to `bijux-rag` are documented here.

This compatibility package exists to preserve the former ingest distribution
name while the canonical package lives at `bijux-canon-ingest`.

Historical release entries below preserve the wording that shipped with tagged
releases when a tagged changelog existed.

## 0.3.6 - 2026-04-20

### Changed

- Prepared the `v0.3.6` release line by aligning fallback versions and inter-package dependency floors across the repository.
- Synchronized release automation and governance with the latest `bijux-std` shared standards baseline.

### Fixed

- `release-pypi.yml` now uses parse-safe publication gating for token/bootstrap checks.
- Protected workflow policy checks now accept shared-manifest-driven standards updates through approved control paths.

## 0.3.5 - 2026-04-19

### Changed

- Compatibility handbook links now resolve canonical ingest package routes at
  `bijux-canon/bijux-canon-ingest/` instead of numbered slug paths.

## 0.3.4 - 2026-04-11

### Fixed

- Compatibility package fallback metadata now aligns with the synchronized
  `v0.3.4` canon release.
- Package README badge links now follow the shared badge catalog and point to
  the exact GHCR package pages used for the legacy distribution and mirrored
  canon package family.

## 0.3.2 - 2026-04-10

### Fixed

- Compatibility package fallback metadata now aligns with the synchronized
  `v0.3.2` canon release.

## 0.3.0 - 2026-04-05

### Added

- Package-local release history for the compatibility distribution so legacy
  installs have a durable migration record instead of relying only on canonical
  package notes.

### Changed

- Compatibility messaging now consistently points new work to
  `bijux-canon-ingest` while preserving the legacy distribution, import, and
  command names.
- PyPI metadata now points legacy `bijux-rag` readers at the canonical
  `bijux-canon-ingest` docs, migration guide, and Bijux-owned package family.
- The package README and overview now document the retired standalone
  repository and use PyPI-safe badge and link targets.
- Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so legacy ingest release expectations stay attached
  to the compatibility package.
- The published docs URL for `bijux-rag` now has its own migration landing
  page inside the shared handbook instead of sending legacy readers directly to
  canonical ingest docs without context.

### Fixed

- Release artifacts now ship the repository license and publish package-local
  ignore rules instead of leaking repo-wide ignore policy into the source
  distribution.

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
