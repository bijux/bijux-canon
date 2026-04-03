# Contributing

bijux-rar is a deterministic core system. Contributions are accepted only if they
preserve determinism, invariants, and repository hygiene.

All changes **must** pass `make all`.

---

## Setup

1. Create a virtual environment.
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
````

3. Run the full pipeline before submitting:

   ```bash
   make all
   ```

PRs that do not pass locally will be rejected.

---

## Contribution Rules

* No generated files may be committed outside `artifacts/`.
* Determinism is non-negotiable.
* Do not relax invariants without explicit migration or versioning.
* Configuration, tooling, and workflows must remain aligned with
  **bijux-cli** and **bijux-rag** conventions.
* Large or architectural changes require prior discussion via issues.

---

## Documentation Contract

Documentation is part of the system contract.

* All documentation must obey `docs/DOC_INVARIANTS.md`.
* Documentation changes must stay aligned with code via
  `docs/DOC_TO_CODE_MAP.md`.
* PRs that introduce doc drift or violate invariants will be rejected.

---

## Contributor Certification

Include the following checklist in your PR description:

* [ ] I have read `docs/CONTRIBUTOR_READING_ORDER.md`
* [ ] I did not weaken or bypass system invariants
* [ ] Any invariant changes include migration and/or versioning
* [ ] Code, tests, and documentation are updated consistently

---

## Scope

bijux-rar is a low-level execution and verification engine.
Feature creep, convenience abstractions, and non-essential integrations
will not be accepted.
