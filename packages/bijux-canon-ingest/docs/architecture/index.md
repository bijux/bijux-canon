# Architecture Overview

This project follows a functional core / explicit-IO boundaries layout:

- `src/bijux_rag/retrieval`: retrieval logic (indexes, embedders, generators, rerankers, ports, domain types).
- `src/bijux_rag/application` + `src/bijux_rag/http` + `src/bijux_rag/serde`: orchestration, transports, and serialization edges.
- `tests/`: unit + e2e + eval suite gates.
- `docs/ADR`: design decisions mirrored from bijux-cli standards (zero-root-pollution, lint/quality/security posture, docstring style).

See ADRs for rationale and trade-offs.

{% include-markdown "../ADR/index.md" %}
