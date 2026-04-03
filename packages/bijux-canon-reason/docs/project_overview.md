STATUS: EXPLANATORY

# Project Overview

`bijux-canon-reason` owns deterministic reasoning execution, trace generation, replay, verification, and evaluation workflows. It should not absorb generic chat orchestration, broad RAG composition, model-hosting concerns, or unrelated benchmark sprawl from other packages.

## Intended tree

```text
src/bijux_canon_reason/
  api/v1/                HTTP boundary, route registration, request guards
  application/           run orchestration and artifact assembly
  core/                  stable contracts, fingerprints, invariants, public compatibility barrel
  core/models/           durable model families for planning, claims, trace, and verification
  evaluation/            evaluation workflows over bundled suites
  execution/             live runtime, replay runtime, tool runtime, executor orchestration, step flow
  interfaces/            CLI, serialization, boundary guards
  planning/              deterministic plan construction
  reasoning/             reasoning backends and extractive logic
  retrieval/             corpus, chunking, BM25 retrieval
  traces/                checksum, replay, diff
  verification/          context, structural checks, provenance checks, verifier
tooling/
  evaluation_suites/     bundled package-owned evaluation inputs
```

## Ownership rules

- `application/` wires package workflows together but does not define core invariants.
- `core/` owns durable public types and integrity rules, while `core/models/` holds the concrete model families that `core/types.py` re-exports for compatibility.
- `execution/` owns runtime behavior, replay behavior, tool invocation surfaces, and step-state orchestration without mixing those concerns into one file.
- `evaluation/` runs and summarizes pinned suites; the suites themselves live under `tooling/`.
- `interfaces/` translates boundary inputs and outputs without becoming business logic.
- `api/v1/` should assemble route modules and guards, not own every endpoint body inline.

## Current posture

- stale `rar` naming was removed from core module names and package-facing docs
- test-only runtime helpers no longer live under `application/`
- application modules now read as run workflow and run artifacts instead of generic buckets
- execution modules distinguish tool runtime from replay runtime and now separate tool dispatch from step-state flow
- verification now separates structural checks from provenance and artifact checks
- API composition now separates request guards, item routes, and run routes
- evaluation suites are package-owned tooling inputs instead of a clumsy root benchmark tree

## Repository guarantees

- `make all` runs real gates in CI
- tests are collected and non-zero
- filesystem writes stay inside `artifacts/bijux-canon-reason/` plus allowed tool caches
- API, docs, replay, and verification drift are checked as package contracts
