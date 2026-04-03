# ARCHITECTURE

`bijux-canon-ingest` is a deterministic document ingestion and retrieval package.

Core layout:
- `docs/LAYOUT.md` is the package map and the first place to check ownership
- `src/bijux_canon_ingest/core/`, `processing/`, and `retrieval/` own durable ingest and retrieval logic
- `src/bijux_canon_ingest/domain/` owns protocols and effect descriptions
- `src/bijux_canon_ingest/infra/` owns concrete adapters
- `src/bijux_canon_ingest/application/` owns orchestration and package-facing service flows
- `src/bijux_canon_ingest/interfaces/cli/` and `interfaces/http/` own external boundaries

The architecture should preserve clear separation between deterministic transforms, adapter code, and user-facing boundaries.
