# PUBLIC_API

`bijux-canon-dev` does not publish an end-user console script.

Its public monorepo-facing API is Python-module based:
- `bijux_canon_dev.api.*`
- `bijux_canon_dev.quality.*`
- `bijux_canon_dev.security.*`
- `bijux_canon_dev.sbom.*`
- `bijux_canon_dev.release.*`
- `bijux_canon_dev.packages.*`

If root `make` targets, CI, or tests import a module directly, treat it as public inside this repository.
