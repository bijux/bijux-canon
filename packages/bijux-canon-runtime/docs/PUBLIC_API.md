# PUBLIC_API

Package-facing surfaces in `bijux-canon-runtime` are:
- console script: `bijux-canon-runtime`
- Python package: `bijux_canon_runtime`
- CLI entrypoint: `bijux_canon_runtime.interfaces.cli.entrypoint`
- API app package: `bijux_canon_runtime.api.v1`
- schema artifacts under `apis/bijux-canon-runtime/v1/`

Internal execution helpers under `runtime/`, `application/`, and `observability/` are implementation detail unless explicitly documented as public.
