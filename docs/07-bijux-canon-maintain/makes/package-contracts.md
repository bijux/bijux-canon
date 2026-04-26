---
title: Package Contracts
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-09
---

# Package Contracts

Shared make behavior for packages should be defined once and reused honestly.

Files such as `makes/bijux-py/package.mk`, `makes/bijux-py/api.mk`,
`makes/bijux-py/api-contract.mk`, `makes/bijux-py/api-freeze.mk`, and
`makes/bijux-py/api-live-contract.mk` describe reusable target contracts that
package-specific files then bind to real repository packages.

## Contract Rule

When package behavior is shared, encode it in a reusable make fragment instead
of copying target logic across many package files.

## Reader Route

- open this page when the main question is where package-level make contracts
  are defined and reused
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/makes/repository-layout/`
  for the wider `makes/` tree structure
- open `https://bijux.io/bijux-canon/07-bijux-canon-maintain/bijux-canon-dev/package-overview/`
  when the question turns from make fragments to maintainer package ownership

