# Rejected designs (maintainer)

This is a lightweight record of decisions we *did not* take, so we don’t re-litigate them every few months.

## 1) Fully dynamic pipeline graphs

Rejected because it weakens auditability and makes traces less comparable across runs.

## 2) Implicit cross-run memory

Rejected because it introduces hidden state and makes replay validation meaningless without external state capture.

## 3) “Best effort” trace metadata

Rejected because partial traces invite overconfident consumers. The system should fail fast rather than emit unverifiable artifacts.
