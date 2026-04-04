# Public API

## Supported entrypoints

- console script: `bijux-canon-runtime`
- Python package: `bijux_canon_runtime`
- CLI entrypoint: `bijux_canon_runtime.interfaces.cli.entrypoint`
- API app package: `bijux_canon_runtime.api.v1`
- schema artifacts under `apis/bijux-canon-runtime/v1/`

## Not automatically public

Internal execution helpers under `runtime/`, `application/`, and `observability/`
are implementation detail unless the package explicitly documents them as stable.
