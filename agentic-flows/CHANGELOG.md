# Changelog  
<a id="top"></a>  

All notable changes to **agentic-flows** are documented here.  
This project adheres to [Semantic Versioning](https://semver.org) and the  
[Keep a Changelog](https://keepachangelog.com/en/1.0.0/) format.  

<a id="unreleased"></a>  
## [Unreleased]  

<!-- unreleased start -->
### Added
* (add new entries via fragments in `changelog.d/`)

### Changed
* (add here)

### Fixed
* (add here)
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
