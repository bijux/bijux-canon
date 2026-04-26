---
title: Catalog
audience: mixed
type: index
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Catalog

The catalog is the concrete half of the compatibility handbook. It tells you
which legacy names still ship, what they preserve, and which canonical package
now owns the real behavior.

These pages should be quick to scan and hard to misread. A reader should be
able to land on an old name, find the current target immediately, and tell
whether the compatibility layer is still thin enough to justify itself.

## Catalog Pages

- [agentic-flows](https://bijux.io/bijux-canon/08-compat-packages/catalog/agentic-flows/)
- [bijux-agent](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-agent/)
- [bijux-rag](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rag/)
- [bijux-rar](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-rar/)
- [bijux-vex](https://bijux.io/bijux-canon/08-compat-packages/catalog/bijux-vex/)
- [Legacy Name Map](https://bijux.io/bijux-canon/08-compat-packages/catalog/legacy-name-map/)
- [Package Behavior](https://bijux.io/bijux-canon/08-compat-packages/catalog/package-behavior/)
- [Import Surfaces](https://bijux.io/bijux-canon/08-compat-packages/catalog/import-surfaces/)
- [Command Surfaces](https://bijux.io/bijux-canon/08-compat-packages/catalog/command-surfaces/)

## Start With

- Open an individual package page when you already know the legacy package
  name.
- Open [Legacy Name Map](https://bijux.io/bijux-canon/08-compat-packages/catalog/legacy-name-map/)
  for the full bridge table.
- Open [Import Surfaces](https://bijux.io/bijux-canon/08-compat-packages/catalog/import-surfaces/)
  or [Command Surfaces](https://bijux.io/bijux-canon/08-compat-packages/catalog/command-surfaces/)
  when the compatibility risk is one public surface rather than one package.

## Checked Surfaces

- legacy distribution names on PyPI
- preserved Python import roots
- preserved CLI names where they still exist
- compatibility package metadata and README routing

## Boundary

The catalog identifies what still exists. It does not justify keeping those
surfaces forever. Retirement and continuity decisions belong in the migration
section.
