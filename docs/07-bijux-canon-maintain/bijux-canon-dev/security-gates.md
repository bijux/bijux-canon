---
title: Security Gates
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Security Gates

Repository-health security checks live in `bijux-canon-dev` when they protect
shared maintenance surfaces instead of one product package. That keeps the
security posture inspectable from checked-in code rather than from vague policy
language.

## Current Gates

- `security/pip_audit_gate.py` for dependency audit enforcement
- maintainer tests that prove the gate's expected behavior
- CI entrypoints that run the security checks through shared target families

## Review Rule

Security documentation is only credible when it names the checked-in tool,
where that tool is called, and what would count as a real regression. If the
page cannot answer those three questions, it is documenting intent instead of
behavior.

## First Proof Check

- `packages/bijux-canon-dev/src/bijux_canon_dev/security`
- `packages/bijux-canon-dev/tests`
- callers in `makes/bijux-py/ci/security.mk` and workflow entrypoints

## Boundary

These gates protect repository health. They should not absorb product-specific
security claims that belong in the canonical package handbooks.
