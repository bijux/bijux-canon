# Changelog  
<a id="top"></a>  

All notable changes to **bijux-canon-runtime** are documented here.

Historical release entries below preserve the wording that shipped with the
tagged release, including legacy distribution naming where applicable.

<a id="unreleased"></a>  
## [Unreleased]  

<!-- unreleased start -->
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

### Fixed
* Duplicate dependency declarations are now rejected during planning.
* Runtime metadata and tests now align with canonical package names and the
  `bijux-cli` `0.3.3` line.
* Root package quality gates were repaired after the refactor series.
* Replay and storage typing, readiness responses, and verification-policy
  override handling were tightened during the runtime refactor series.
<!-- unreleased end -->  

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
