---
title: Package Dispatch
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-dev-docs
last_reviewed: 2026-04-26
---

# Package Dispatch

Package dispatch is how shared target families become package-specific work
without copying the whole command model. It is the seam where reusable rules
meet real package directories and artifact locations.

## Dispatch Surfaces

- `makes/bijux-py/root/package-dispatch.mk` for shared dispatch mechanics
- `makes/packages/bijux-canon-*.mk` for canonical package bindings
- `makes/packages/compat-package.mk` for compatibility-package routing
- `makes/bijux-py/package-catalog.mk` for shared package metadata

## What Dispatch Must Not Do

Dispatch should map shared rules onto package inputs. It should not smuggle new
package behavior into the make layer or hide package-specific differences that
belong in the package itself.

## First Proof Check

- `makes/bijux-py/root/package-dispatch.mk`
- `makes/packages/bijux-canon-*.mk`
- `makes/packages/compat-package.mk`
