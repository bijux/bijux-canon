---
title: Retirement Playbook
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-compat-docs
last_reviewed: 2026-04-26
---

# Retirement Playbook

Compatibility packages should leave the repository by a visible process, not by
wishful thinking or surprise. Retirement is the final migration step, so it
needs the same discipline as the initial bridge.

## Retirement Steps

1. Confirm which supported environments still depend on the legacy name.
2. Verify that canonical docs and migration guidance have been stable long
   enough to support the move.
3. Search the repository for remaining legacy dependency, import, and command
   usage.
4. Update metadata, docs, and release notes so the retirement is explicit.
5. Remove the package only when the remaining dependence is understood rather
   than guessed.

## Evidence To Gather

- support or usage evidence for the remaining legacy name
- published migration guidance that has stayed current
- validation that supported automation no longer depends on the compatibility
  package
