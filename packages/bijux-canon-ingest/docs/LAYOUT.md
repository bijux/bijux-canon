# LAYOUT

`bijux-canon-ingest` should stay organized around stable ownership boundaries.

Ideal tree:

```text
packages/bijux-canon-ingest/
├── pyproject.toml
├── README.md
├── docs/
│   ├── index.md
│   ├── LAYOUT.md
│   ├── ARCHITECTURE.md
│   ├── BOUNDARIES.md
│   └── ...
├── src/bijux_canon_ingest/
│   ├── __init__.py
│   ├── application/
│   ├── config/
│   ├── core/
│   ├── domain/
│   ├── infra/
│   ├── interfaces/
│   ├── observability/
│   ├── processing/
│   ├── retrieval/
│   └── package-local utility subpackages
├── stubs/
└── tests/
    ├── unit/
    ├── e2e/
    ├── eval/
    └── invariants/
```

Source ownership:

- `application/`: package-local orchestration, service facades, and workflow assembly
- `config/`: configuration models and builders for ingest-facing flows
- `core/`: durable ingest rules, predicates, and shared pure value-level helpers
- `domain/`: pure protocols and effect descriptions that define ingest behavior
- `infra/`: concrete adapters that implement domain capabilities
- `interfaces/`: CLI, HTTP, serialization, and boundary-specific error translation
- `observability/`: trace and observation data structures for ingest execution
- `processing/`: deterministic document cleaning, chunking, and pipeline stages
- `retrieval/`: index construction, retrieval contracts, and retrieval-domain models

Package-local but extraction candidates:

- `fp/`, `result/`, `streaming/`, `tree/`, `safeguards/`, and `integrations/` are currently useful here, but they are generic enough that they could eventually move to a shared package if another package needs the same abstractions without ingest-specific coupling.
- Those modules should remain dependency-light and free of CLI, HTTP, runtime, or repository concerns so extraction stays possible.

What should not live here:

- standalone vector execution engines or cross-package index authorities
- runtime-wide storage, replay, or governance concerns
- monorepo tooling, release automation, or developer-only helpers
- package-external business logic that belongs to another package boundary

Test layout expectations:

- `tests/unit/` should mirror top-level source areas that own behavior
- `tests/e2e/` should cover package-facing CLI, HTTP, and service contracts
- `tests/eval/` should hold pinned retrieval fixtures and offline corpora
- `tests/invariants/` should protect layout rules and generated-file hygiene

Directory hygiene:

- generated caches such as `__pycache__`, `.pytest_cache`, and `.ruff_cache` must never be treated as package content
- documentation should describe durable ownership, not migration steps or temporary sequencing
