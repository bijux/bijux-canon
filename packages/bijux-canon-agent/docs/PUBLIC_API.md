# PUBLIC_API

Published package-facing surfaces are:
- console script: `bijux-canon-agent`
- Python package: `bijux_canon_agent`
- CLI entrypoint module: `bijux_canon_agent.interfaces.cli.entrypoint`
- HTTP app package: `bijux_canon_agent.api.v1`

Stable imports should be deliberate. Internal modules under `agents/`, `pipeline/`, and `observability/` are implementation space unless they are explicitly documented as public.
