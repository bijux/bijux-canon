# Architecture Overview

This project follows a functional core / explicit-IO boundaries layout:

- `src/bijux_rag/rag`: domain logic (indexes, embedders, generators, rerankers, app orchestration).
- `src/bijux_rag/boundaries`: adapters (FastAPI, CLI, file shims).
- `tests/`: unit + e2e + eval suite gates.
- `docs/ADR`: design decisions mirrored from bijux-cli standards (zero-root-pollution, lint/quality/security posture, docstring style).

See ADRs for rationale and trade-offs.

{% include-markdown "../ADR/index.md" %}
