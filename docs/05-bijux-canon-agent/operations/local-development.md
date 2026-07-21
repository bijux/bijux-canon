---
title: Local Development
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-agent-docs
last_reviewed: 2026-07-21
---

# Local Development

Develop agent behavior as a causal workflow. A final response is insufficient
evidence: the useful local loop proves which role acted, which lifecycle
transition authorized it, which provider configuration applied, what was
recorded, and why the controller stopped.

```mermaid
flowchart LR
    C[Change orchestration contract] --> F[Run focused workflow fixture]
    F --> T[Inspect ordered trace]
    T --> O[Reconstruct terminal outcome]
    O --> B{Provider or interface changed?}
    B -- no --> P[Run package gate]
    B -- yes --> X[Run adapter or API evidence]
    X --> P
```

## Bootstrap from the repository root

```bash
make install
make -f makes/packages/bijux-canon-agent.mk \
  -C packages/bijux-canon-agent help
```

Run normal gates through root dispatch:

```bash
make test PACKAGE=bijux-canon-agent
make lint PACKAGE=bijux-canon-agent
make quality PACKAGE=bijux-canon-agent
```

The package profile provisions `packages/bijux-canon-agent/.venv` and routes
reports into `artifacts/`. There is no package-local Makefile; direct invocation
requires the repository profile path.

## Start with the nearest workflow invariant

```bash
packages/bijux-canon-agent/.venv/bin/python -m pytest \
  packages/bijux-canon-agent/tests/<area>/<test-file>.py -q
```

| Changed behavior | Evidence to inspect |
| --- | --- |
| role contract | typed input, typed success, veto, error, and handoff serialization |
| lifecycle controller | allowed transition, forbidden transition, abort, and terminal state |
| merge or judgment | input lineage, score, issues, action plan, decision, and confidence |
| convergence | window, strategy, verdict history, stable stop reason, and non-convergence |
| provider adapter | selected provider/model, parameters, timeout, usage, failure, and redaction |
| retry or fallback | attempt order, budget, provider change, error evidence, and final classification |
| trace | header, ordered entries, hashes, observational exclusions, and completeness |
| finalization | parity between trace-derived outcome and `final_result.json` |

Use local or stub providers for deterministic contract work. Live-provider
tests answer connectivity and integration questions; they cannot establish
historical replay or answer correctness.

## Handle credentials without weakening tests

The current CLI bootstrap checks all supported provider credential variables
before command dispatch, including help and replay. Tests should supply
controlled non-secret values or bypass the CLI at an owned lower interface.
Never place live keys in fixtures, YAML, traces, logs, snapshots, or committed
environment files.

Provider tests must prove redaction and failure behavior. A successful call is
not sufficient when a timeout, rate limit, malformed response, or provider
fallback can change workflow control.

## Validate public surfaces deliberately

For HTTP or OpenAPI changes:

```bash
make api PACKAGE=bijux-canon-agent
```

The v1 HTTP application uses a fixed offline pipeline. Do not claim parity with
the provider-configurable CLI beyond their shared typed outcome contract.

For entry points, root imports, package data, extras, or distribution metadata:

```bash
make build PACKAGE=bijux-canon-agent
```

Use `make docs-check` when role, trace, convergence, provider, artifact, or
replay terminology changes.

## Preserve result and trace together

Every material fixture should retain the pipeline definition, resolved
configuration hash, provider metadata, ordered trace, terminal outcome, stop
reason, termination reason, confidence, and epistemic verdict. The result and
trace must reconcile even for veto, abort, partial failure, and dry-run paths.

See [change validation](../quality/change-validation.md) and
[artifact contracts](../interfaces/artifact-contracts.md) for the evidence
expected at review.
