# Release Checklist (v0.1.0)
> Release seal: closure, alignment, and declaration only.

## 1. Freeze scope (absolute)
- Only clarification, hardening, or removal allowed.
- No new APIs.
- No new policy semantics.
- No new execution paths.
- No refactors unless required for correctness.
- Any observable behavior change defers to v0.2.0.

## 2. Align versioning with agentic-proteins (dynamic only)
- Versioning derives from VCS tags; no static version fields.
- Tagged builds must not include .dev or local suffixes.
- `git tag v0.1.0` is the source of truth for artifacts.

## 3. Align project metadata with agentic-proteins
- Metadata is crisp, technical, and non-marketing.
- Description explicitly mentions governed non-deterministic execution.
- Keywords are concrete and searchable.
- Classifiers reflect current maturity (no production/stable claims).

## 4. Declare non-determinism status (once, clearly)
- Canonical statement present in README and docs entry point only.

## 5. Eliminate misleading or dead surfaces
- No legacy paths, shims, or compatibility placeholders.
- No unused CLI flags.
- No undocumented environment variables.
- No placeholder policy presets exposed publicly.
- No commented-out or “future” code paths.

## 6. Lock API guarantees to schema only
- OpenAPI schema is frozen for v0.1.0.
- Schema compatibility is the only API guarantee.
- Runtime behavior, policy interpretation, and enforcement may evolve.

## 7. Normalize failure language and taxonomy
- CLI output, API errors, replay verdicts, and verification failures map to named failure classes.
- Reasons are deterministic, inspectable, and auditable.
- No apologetic or speculative phrasing.

## 8. Write release notes (one page, hard truth)
- Structure: What it is / What it is not / Who it is for / What comes next.
- No hype, no roadmap, no promises.

## 9. Final artifact hygiene
- Final artifacts only: wheel, sdist, SBOM (prod + dev), citation outputs, OpenAPI schema, test + API JUnit reports.
- Remove intermediate builds, local-only outputs, and .dev artifacts.

## 10. `agentic-flows --help` must succeed
- Must work without editable installs, dev extras, local paths, or hidden assumptions.
