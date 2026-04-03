# Release dry-run checklist

Use this before tagging to avoid publishing broken artifacts.

- Clean tree; `make lint quality security api test` green.
- `make api` regenerates schema with no drift.
- Build wheel locally: `python -m build` (or `make release` if enabled).
- Install wheel in a fresh venv, run `bijux vex --help`, and execute a deterministic flow end-to-end.
- `mkdocs build --strict` succeeds (docs reachable, no warnings).
- SBOM generated (`make sbom`) with zero unignored vulns.
- Confirm README badges and links resolve.
