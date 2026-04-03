# Tooling & Make targets

Front-door commands (mirrors bijux-cli):

- `make fmt` — ruff format + autofix
- `make lint` — ruff check + mypy (artifacts in `artifacts/bijux-llm-rag/lint`)
- `make test` — unit + e2e + coverage (artifacts/bijux-llm-rag/test)
- `make api` — OpenAPI lint + drift + Schemathesis
- `make docs` — mkdocs build (strict) → `artifacts/bijux-llm-rag/docs/site`
- `make quality` — vulture/deptry/interrogate
- `make security` — bandit + pip-audit (gating)
- `make sbom` — CycloneDX SBOMs
- `make all` — clean → install → test → lint → quality → security → api → docs → build → sbom

All caches and artifacts are redirected under `artifacts/bijux-llm-rag/` to keep the repo root clean.
