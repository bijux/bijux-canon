# Changelog  
<a id="top"></a>  

All notable changes to **bijux-canon-runtime** are documented here.

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

* Runtime schema-hash packaging and stability-test guidance now reference
  canonical API paths under `apis/bijux-canon-runtime/v1`.
* Package contract docs and shared handbook links now resolve canonical runtime
  handbook routes without numbered slug targets.

## [0.3.4] - 2026-04-11

### Fixed

* Runtime release metadata now falls back to `0.3.4` when tag metadata is not
  available during local validation.
* Internal canon package dependency floors now require the synchronized
  `0.3.4` package line.
* Package README badge links now follow the shared badge catalog and point to
  the exact GHCR package pages used for published runtime bundles.

## [0.3.2] - 2026-04-10

### Fixed

* Runtime release metadata now falls back to `0.3.2` when tag metadata is not
  available during local validation.
* Internal canon package dependency floors now require the synchronized
  `0.3.2` package line.

<a id="v0-3-0"></a>  
## [0.3.0] - 2026-04-05  

<!-- release-v0-3-0 start -->
### Added
* Package-local documentation now explains execution authority, replay
  semantics, operator boundaries, API contract testing, and example datasets in
  clearer human-facing language.
* Runtime now has focused package tests for command mapping, execution
  persistence, canonical package-version lookup, and identifier exports.

### Changed
* The package was realigned under the canonical `bijux-canon-runtime` identity,
  with runtime models, contracts, ontology, observability, interfaces, and API
  surfaces renamed around durable ownership.
* Execution orchestration was decomposed into smaller modules for flow
  preparation, step execution, run recording, replay analysis, policy handling,
  and persistence support.
* Runtime command handling, `RunMode` ownership, and non-determinism lifecycle
  plumbing were consolidated into clearer runtime-facing modules.
* Planner behavior now uses normalized dependency ordering and canonical package
  version discovery for runtime metadata.
* Flow preparation, execution recording, replay analysis, tool-event recording,
  verification arbitration, and persistence support were split into smaller
  modules so runtime behavior is easier to reason about and maintain.
* PyPI metadata, search keywords, and project URLs now make the canonical
  runtime package easier to discover from package indexes and Bijux-owned docs.
* The package README now uses PyPI-safe badge and link targets, and it points
  legacy `agentic-flows` users to the canonical migration path and retired
  repository guidance.
* Package-local PyPI publication guidance is now checked in and shipped with
  the source distribution so runtime release expectations stay durable.
* Source distributions now publish package-local ignore rules instead of a
  generic repo-level `.gitignore`.

### Fixed
* Duplicate dependency declarations are now rejected during planning.
* Runtime metadata and tests now align with canonical package names and the
  `bijux-cli` `0.3.3` line.
* Root package quality gates were repaired after the refactor series.
* Replay and storage typing, readiness responses, and verification-policy
  override handling were tightened during the runtime refactor series.
* Release artifacts now ship the repository `LICENSE` file so downstream
  consumers receive the license text with the published package.
<!-- release-v0-3-0 end -->  

---  

<!-- release start -->  

<a id="v0-1-0"></a>  
## [0.1.0] – 2025-01-21  

### Added
- **Core runtime**
  - Deterministic execution lifecycle with planning, execution, and finalization phases.
  - Execution modes: plan, dry-run, live, observe, and unsafe.
  - Strict determinism guardrails with explicit seed and environment fingerprints.
- **Non-determinism governance**
  - Declared non-determinism intent model and policy validation.
  - Entropy budgeting with enforcement, exhaustion semantics, and replay analysis.
  - Determinism profiles with structured replay metadata.
- **Replay and audit**
  - Replay modes (strict/bounded/observational) and acceptability classifications.
  - Trace diffing, replay envelopes, and deterministic replay validation.
  - Observability capture for events, artifacts, evidence, and entropy usage.
- **Persistence**
  - DuckDB execution store with schema contract enforcement and migrations.
  - Execution schema, replay envelopes, checkpoints, and trace storage.
- **CLI + API surface**
  - CLI commands for planning, running, replaying, inspecting, and diffing runs.
  - OpenAPI schema for the HTTP surface with schema hash stability checks.
- **Policies and verification**
  - Verification policy and arbitration plumbing for reasoning and evidence checks.
  - Failure taxonomy with deterministic error classes.
- **Docs and examples**
  - Determinism/non-determinism contract docs and storage model guidance.
  - Examples for deterministic and replay behavior.
- **Quality gates**
  - Makefile orchestration for tests, linting, docs, API checks, SBOM, and citation outputs.


<!-- release end -->
