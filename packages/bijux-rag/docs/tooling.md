# Tooling & Make targets

Front-door commands (mirrors bijux-cli):

- `make fmt` — ruff format + autofix
- `make lint` — ruff check + mypy + pytype (artifacts in `artifacts/bijux-rag/lint`)
- `make test` — unit + e2e + coverage (artifacts/bijux-rag/test)
- `make api` — OpenAPI lint + drift + Schemathesis
- `make docs` — mkdocs build (strict) → `artifacts/bijux-rag/docs/site`
- `make quality` — vulture/deptry/interrogate
- `make security` — bandit + pip-audit (gating)
- `make sbom` — CycloneDX SBOMs
- `make all` — clean → install → test → lint → quality → security → api → docs → build → sbom

All caches and artifacts are redirected under `artifacts/bijux-rag/` to keep the repo root clean.
