# CONTRACTS

Stable contracts in `bijux-canon-index` are:
- API schemas under `apis/bijux-canon-index/v1/`
- plugin entrypoint groups under `bijux_canon_index.vectorstores`, `bijux_canon_index.embeddings`, and `bijux_canon_index.runners`
- public HTTP surface under `src/bijux_canon_index/api/v1/`
- stable package-facing models and errors under `src/bijux_canon_index/core/` and `interfaces/schemas/`

The package does not currently declare a published console script in `pyproject.toml`. Treat CLI internals as operator tooling unless explicitly promoted.
