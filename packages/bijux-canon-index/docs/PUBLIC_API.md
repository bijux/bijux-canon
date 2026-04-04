# Public API

The supported surface of `bijux-canon-index` is primarily package and schema based.

## Supported entrypoints

- Python package: `bijux_canon_index`
- HTTP app builder: `bijux_canon_index.api.v1.build_app`
- pinned API schema artifacts under `apis/bijux-canon-index/v1/`
- plugin entrypoint contracts for vector stores, embeddings, and runners

## Not automatically public

Deep orchestration helpers and backend adapters are implementation detail unless
the package explicitly documents them as stable extension points.
