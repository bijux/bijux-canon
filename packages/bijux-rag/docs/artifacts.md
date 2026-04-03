# Artifacts & Outputs

All tooling writes under `artifacts/bijux-rag/` to maintain zero root pollution. Key locations:

- `artifacts/bijux-rag/test/`: pytest caches, coverage (`.coverage`, `coverage.xml`, `htmlcov/`), junit XML.
- `artifacts/bijux-rag/lint/`: ruff and mypy reports.
- `artifacts/bijux-rag/api/`: OpenAPI drift output, schemathesis logs.
- `artifacts/bijux-rag/docs/`: mkdocs site output (when using docs targets).
- `artifacts/bijux-rag/security/`: bandit and pip-audit reports.
- `artifacts/bijux-rag/sbom/`: SBOM outputs.

If you see cache or report files at repository root, remove the offender before committing.
