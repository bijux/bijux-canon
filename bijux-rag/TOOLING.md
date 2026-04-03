# Tooling & Make targets

Front-door commands (mirrors bijux-cli):

- `make fmt` — ruff format + autofix
- `make lint` — ruff check + mypy + pyright (artifacts in `artifacts/lint`)
- `make type` — pyright (also run via `make lint`)
- `make test` — unit + e2e + coverage (artifacts/test)
- `make api` — OpenAPI lint + drift + Schemathesis
- `make docs` — mkdocs build (strict) → `artifacts/docs/site`
- `make quality` — vulture/deptry/reuse/interrogate
- `make security` — bandit + pip-audit (gating)
- `make sbom` — CycloneDX SBOMs
- `make hygiene` — zero-root-pollution gate
- `make all` — clean → install → test → lint → quality → security → api → docs → build → sbom → citation → hygiene

All caches and artifacts are redirected under `artifacts/` to keep the repo root clean.
