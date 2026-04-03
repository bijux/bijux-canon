# ADR-0005: Enforcing Zero-Root-Pollution via Makefile-Orchestrated Artifact Containment

* **Date:** 2025-08-20
* **Status:** Accepted
* **Author:** Bijan Mousavi

## Context

Build, test, docs, and release steps produce transient outputs (wheels/sdists, coverage reports, HTML sites, schemas). When these spill into the repo root or source trees, they clutter the working copy, risk accidental commits, and make CI/release packaging brittle.

## Decision

All generated outputs **must** be written beneath a single top-level directory: `artifacts/`. Each package owns a dedicated subtree inside that root, and bijux-rag writes only to `artifacts/bijux-rag/`. No Make/Tox/CI task may write transient files to the repo root or source trees. Standard caches (e.g., `.venv/`, `.tox/`, `.pytest_cache/`) are permitted and ignored via `.gitignore`.

This policy is enforced **centrally by the Makefile system**. The package
`Makefile` and the root-managed `../../makes/bijux-rag/*` modules define
orchestration and output paths (`PROJECT_ARTIFACTS_DIR = artifacts/bijux-rag`). Tox and GitHub
Actions **call Make targets**; they do not choose paths.

### Canonical Layout (Generated Only)

```
artifacts/
  bijux-rag/
    build/          # wheels/sdists built locally
    docs/
      site/         # MkDocs output
    test/
      htmlcov/      # coverage HTML
      coverage.xml  # coverage XML
      junit*.xml    # test reports
      hypothesis/   # Hypothesis DB
      benchmarks/   # benchmark results
      tmp/          # temp test files
    api/            # schemas, API logs/reports
    sbom/           # SBOM outputs
    quality/        # interrogate, vulture, deptry, and related reports
    security/       # bandit, pip-audit, etc.
    lint/           # linter/type checker reports
```

> Note: Locally we emit to `artifacts/bijux-rag/build/`. In CI, the uploaded artifact named **`dist`** still represents that same build bundle after upload/download.

Tracked sources (e.g., `pyproject.toml`, `README.md`, `LICENSE`) remain in place and are **not** artifacts.

## Rationale

* **Clean Working Tree:** Routine tasks don’t dirty the repo; `git status` stays meaningful.
* **Deterministic Pipelines:** CI and docs deploy hydrate exclusively from `artifacts/bijux-rag/**`.
* **Curated Releases:** GitHub Releases contain concise, named bundles (ZIP/tar.gz per subtree), not thousands of loose files.
* **Safe Docs Builds:** MkDocs reads the tracked `docs/` tree and writes to `artifacts/bijux-rag/docs/site`; required pages are asserted.
* **Reproducibility:** Uniform paths across local and CI; caches remain standard and ignored.

## Enforcement

### Local (Make + Tox)

* `PROJECT_ARTIFACTS_DIR = artifacts/bijux-rag` in the package `Makefile`; sub-recipes in
  `../../makes/bijux-rag/*` route outputs under that root (for example,
  `../../makes/bijux-rag/test.mk` → `artifacts/bijux-rag/test/`; integrates with
  ADR-0004 toolchain targets like `make lint` for logs/caches under
  `artifacts/bijux-rag/lint/`).
* Tox environments call Make targets; they do **not** set output paths directly.
* Docs build directly from the tracked `docs/` directory and publish to `artifacts/bijux-rag/docs/site`.

### CI (GitHub Actions)

* **`ci.yml`** (CI workflow) uploads only from `artifacts/bijux-rag/**`.
* **`deploy-docs.yml`** (Deploy Docs workflow) builds into `artifacts/bijux-rag/docs/site` and checks required pages.
* **`publish.yml`** (Publish to PyPI workflow) assembles release bundles from `artifacts/bijux-rag/**`, computes checksums for the build bundle, and attaches curated ZIPs (tests per-py, lint, quality, security, api, docs, sbom, build).

## Consequences

### Positive

* Consistent paths locally and in CI.
* Simpler evidence collection and release packaging.
* Lower risk of committing transients.
* Docs completeness enforced before deploy.

### Trade-offs

* Some tools require output redirection or a post-step move (handled in Make).
* Initial refactors to Make/Tox; validated by CI.
* PRs introducing new tools must adhere to the layout (review + CI enforce it).

## Invariants

* Make targets do **not** write outside `$(PROJECT_ARTIFACTS_DIR)` (except standard caches). 
* CI uploads/downloads **only** `artifacts/bijux-rag/**`. 
* Docs build from `docs/` → `artifacts/bijux-rag/docs/site`. 
* Releases assemble from `artifacts/bijux-rag/**`.

## Compliance Examples

* **Build Wheels/SDist**

  ```bash
  python -m build --outdir artifacts/bijux-rag/build
  ```

* **Tests + Coverage + JUnit**

  ```bash
  pytest --cov \
         --cov-report=xml:artifacts/bijux-rag/test/coverage.xml \
         --cov-report=html:artifacts/bijux-rag/test/htmlcov \
         --junitxml=artifacts/bijux-rag/test/junit.xml
  ```

* **MkDocs**

  ```yaml
  docs_dir: docs
  site_dir: artifacts/bijux-rag/docs/site
  ```

## Alternatives Considered

* Tool defaults scattered across the repo — rejected (clutter, fragility). 
* Per-tool output roots — rejected (fragmentation). 
* CI-only containment — rejected (misses local benefits).
