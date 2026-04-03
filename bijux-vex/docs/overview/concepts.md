# Conceptual overview

This page is descriptive, not normative. It explains bijux-vex in plain language without APIs or enums.

## What bijux-vex is
- A vector execution engine: it runs vector similarity computations under explicit contracts.
- Contracts come in two flavors:
  - **Deterministic**: exact algorithms, replayable outputs, bit-stable provenance.
  - **Non-deterministic (experimental)**: ANN/approximate algorithms, bounded divergence, declared randomness.
- Every run is tied to an execution plan, provenance, and artifacts that record how results were produced.

## Vector execution vs. vector DB
- Vector DBs focus on storage and serving; execution is implicit and often approximate by default.
- bijux-vex focuses on execution semantics: what was run, under which guarantees, and how to replay or compare results.
- Artifacts, plans, and provenance are first-class; storage backends are just sources and ledgers.

## Core objects (conceptual)
- **Execution plan**: the declared algorithm, contract, and parameters.
- **Execution artifact**: the outputs plus provenance and signatures.
- **Provenance**: the audit trail that explains how the artifact was produced.
- **Randomness profile**: where nondeterminism enters and how it is bounded.

## How determinism works here
- Deterministic runs use exact search and must replay identically.
- Non-deterministic runs must emit approximation reports and randomness metadata; replay checks envelopes, not equality.

## How to approach the docs
- If you want rules: go to `spec/system_contract.md` and `spec/execution_contracts.md`.
- If you want rationale: see `design/why_vector_execution.md` and `design/contracts.md`.
- If you want to run something: start with `examples/overview.md`.
