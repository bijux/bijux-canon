# Artifacts & Outputs

All tooling writes under `artifacts/bijux-canon-ingest/` to maintain zero root pollution. Key locations:

- `artifacts/bijux-canon-ingest/test/`: pytest caches, coverage (`.coverage`, `coverage.xml`, `htmlcov/`), junit XML.
- `artifacts/bijux-canon-ingest/lint/`: ruff and mypy reports.
- `artifacts/bijux-canon-ingest/api/`: OpenAPI drift output, schemathesis logs.
- `artifacts/bijux-canon-ingest/docs/`: mkdocs site output (when using docs targets).
- `artifacts/bijux-canon-ingest/security/`: bandit and pip-audit reports.
- `artifacts/bijux-canon-ingest/sbom/`: SBOM outputs.

If you see cache or report files at repository root, remove the offender before committing.
