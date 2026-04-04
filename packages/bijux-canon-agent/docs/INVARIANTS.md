# Invariants

These are the truths maintainers should defend even during aggressive refactors.

- every meaningful execution remains explainable through traces and result artifacts
- runtime governance stays outside this package
- CLI and HTTP layers stay thin enough that the core workflow remains reusable
- generated output never becomes hand-maintained source
- role-local logic stays near the role instead of disappearing into orchestration sprawl

If a change improves convenience by weakening auditability, boundary clarity, or
trace quality, it is probably a regression.
