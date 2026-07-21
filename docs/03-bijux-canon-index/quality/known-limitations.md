---
title: Known Limitations
audience: mixed
type: reference
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-07-21
---

# Known Limitations

The package can make retrieval decisions inspectable; it cannot make an
approximate algorithm exact, guarantee that a remote backend remains stable,
or establish that the indexed corpus is correct.

## Approximation and backend limits

- Non-deterministic execution is a bounded, explicitly declared surface. ANN
  libraries may still vary by implementation version, build flags, hardware,
  concurrency, and index construction order.
- A seed controls only randomness honored by the selected runner. It does not
  neutralize unrecorded backend nondeterminism.
- Strict replay can compare recorded ANN identity and parameters only when the
  runner exposes that metadata. Missing provenance is a refusal boundary, not
  evidence that the environment was unchanged.
- Cross-backend conformance protects common contracts, not identical ranking.
  Exact and ANN execution can legitimately return different neighbors.
- Optional FAISS, HNSW, and Qdrant integrations add their own installation,
  availability, persistence, retry, and version constraints.

## Quality and budget limits

Retrieval correctness means the engine honored its declared plan. It does not
mean the embedding model represents the domain well or that the returned
evidence is sufficient for a conclusion. Compare ANN outcomes with an exact
baseline and use domain evaluation data before setting quality bounds.

Latency and memory budget fields are currently enforced through deterministic
execution-cost estimates and counter proxies, not operating-system resource
meters. They are useful contract bounds and regression signals, but they are
not wall-clock deadlines or process memory limits. Infrastructure-level
resource enforcement remains the caller's responsibility.

## Persistence and interface limits

- The filesystem `RunStore` uses atomic file replacement for individual JSON
  records. It is not a multi-host transactional database and does not provide
  distributed locking.
- Incomplete and failed runs are retained for diagnosis but cannot be loaded as
  complete outcomes.
- Artifact portability depends on supported canonical versions, backend
  metadata, and available adapters. A portable execution record does not
  bundle an external vector database or ANN binary.
- The package contains a Typer application but currently does not publish a
  `bijux-canon-index` console-script entry point. Direct library/API use and
  module invocation remain available; automation should not assume that
  command name is installed.

## Security boundary

Authorization contracts and metadata redaction operate inside the package's
declared interfaces. Deployment authentication, transport security, secret
storage, tenant isolation, and backend access control must be supplied by the
hosting system. Provenance should record identifiers and decisions without
copying secrets into result artifacts.

Use exact execution when equality is required. Use ANN only when the execution
intent, acceptable loss, budget, randomness, and replay policy are all explicit
enough for a later reviewer to interpret divergence.
