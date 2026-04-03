# Artifacts & Outputs

All tooling writes under `artifacts/bijux-llm-rag/` to maintain zero root pollution. Key locations:

- `artifacts/bijux-llm-rag/test/`: pytest caches, coverage (`.coverage`, `coverage.xml`, `htmlcov/`), junit XML.
- `artifacts/bijux-llm-rag/lint/`: ruff and mypy reports.
- `artifacts/bijux-llm-rag/api/`: OpenAPI drift output, schemathesis logs.
- `artifacts/bijux-llm-rag/docs/`: mkdocs site output (when using docs targets).
- `artifacts/bijux-llm-rag/security/`: bandit and pip-audit reports.
- `artifacts/bijux-llm-rag/sbom/`: SBOM outputs.

If you see cache or report files at repository root, remove the offender before committing.
