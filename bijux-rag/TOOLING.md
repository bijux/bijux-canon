# Tooling & Make targets

Front-door commands (mirrors bijux-cli):

- `make fmt` — ruff format + autofix
- `make lint` — ruff check + mypy + pytype (artifacts in `artifacts/lint`)
- `make test` — unit + e2e + coverage (artifacts/test)
- `make api` — OpenAPI lint + drift + Schemathesis
- `make docs` — mkdocs build (strict) → `artifacts/docs/site`
- `make quality` — vulture/deptry/reuse/interrogate
- `make security` — bandit + pip-audit (gating)
- `make sbom` — CycloneDX SBOMs
- `make hygiene` — zero-root-pollution gate
- `make all` — clean → install → test → lint → quality → security → api → docs → build → sbom → hygiene

All caches and artifacts are redirected under `artifacts/` to keep the repo root clean.
