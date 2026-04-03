# Artifacts & Outputs

All tooling writes under `artifacts/` to maintain zero root pollution. Key locations:

- `artifacts/test/`: pytest caches, coverage (`.coverage`, `coverage.xml`, `htmlcov/`), junit XML.
- `artifacts/lint/`: ruff/mypy/pyright/pytype reports.
- `artifacts/api/`: OpenAPI drift output, schemathesis logs.
- `artifacts/docs/`: mkdocs site output (when using docs targets).
- `artifacts/security/`: bandit and pip-audit reports.
- `artifacts/sbom/`: SBOM outputs.

If you see cache or report files at repository root, run `make hygiene` and fix the offender before committing.
