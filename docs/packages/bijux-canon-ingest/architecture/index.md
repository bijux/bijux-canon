# Architecture Overview

This project follows a functional core / explicit-IO boundaries layout:

- `src/bijux_canon_ingest/core`, `processing`, `retrieval`, `domain`, `result`, `streaming`, and `tree`: pure or mostly-pure core logic.
- `src/bijux_canon_ingest/application`: orchestration surfaces split by responsibility (`pipeline`, `pipeline_definitions`, `indexing`, `querying`, `service`).
- `src/bijux_canon_ingest/interfaces`: transport and boundary adapters (`cli`, `http`, `serialization`, `errors`).
- `src/bijux_canon_ingest/observability`: trace, taps, and deterministic execution summaries.
- `src/bijux_canon_ingest/integrations` and `safeguards`: optional ecosystem adapters and cross-cutting runtime protection.
- `src/bijux_canon_ingest/infra`: pluggable runtime adapters such as storage and clocks.
- `tests/`: unit + e2e + eval suite gates.
- `ADR/`: design decisions mirrored from bijux-cli standards (zero-root-pollution, lint/quality/security posture, docstring style).

See ADRs for rationale and trade-offs.

{% include-markdown "../ADR/index.md" %}
