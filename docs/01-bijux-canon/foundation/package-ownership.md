---
title: Package Ownership
audience: mixed
type: reference
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-08-21
---

# Package Ownership

Every production decision has one canonical owner. Other packages may consume
the owner's versioned artifacts or ports, but they must not reproduce the
decision, infer it from private state, or acquire it through a compatibility
name. Runtime is the sole composition root; repository tooling verifies the
boundaries without becoming another product implementation.

## Exclusive Responsibilities

| Distribution family | Exclusive production responsibility | Does not own |
| --- | --- | --- |
| `bijux-canon-ingest` | discovering sources, parsing safely, normalizing content, preserving exact locators, chunking, and publishing immutable corpus snapshots and deltas | embeddings, retrieval ranking, claims, agent transitions, or run persistence |
| `bijux-canon-index` | managing embedding and index lifecycles and producing capability-checked lexical or vector retrieval results with witnesses and hit provenance | document parsing, answer synthesis, agent state, or top-level jobs |
| `bijux-canon-reason` | turning retrieved evidence into evidence packets, atomic claims, citations, claim graphs, synthesis, and support, opposition, ambiguity, or insufficiency decisions | index storage, implicit credential discovery, agent scheduling, or run persistence |
| `bijux-canon-agent` | executing bounded research roles, plans, tool policy, counterevidence loops, budgets, checkpoints, convergence, and causal agent traces | concrete databases or indexes, provider discovery, or top-level persistence |
| `bijux-canon-runtime` | composing installed package ports into typed operations and durable jobs, dispatching adapters, applying run policy, persisting CAS and DuckDB records, and providing inspect, replay, compare, resume, and cancellation behavior | alternate parsing, retrieval, reasoning, or agent-domain decisions |
| `bijux-canon-dev` | repository inventory, contract and schema generation, evidence tooling, and delivery validation | user-facing behavior or domain policy |
| compatibility distributions | preserving one legacy distribution, import, module, and command surface as a thin alias to exactly one canonical owner, with migration and deprecation guidance | independent domain logic, translated results, a second canonical owner, or release truth that differs from the owner |

An ownership boundary follows the decision, not the current call site. For
example, runtime may schedule retrieval and persist its result, but index still
decides whether a backend can execute the retrieval plan and how result
provenance is represented.

## Dependency Direction

The installed dependency graph must preserve these directions:

```text
runtime -> ingest, index, reason, agent
runtime -> agent ports -> reason and index ports
index -> ingest artifact contracts
reason -> evidence and provider ports
compatibility distribution -> exactly one canonical owner
repository checks -> public contracts and package metadata
```

The inverse edges are forbidden. Ingest must not import index, reason, agent,
or runtime. Reason must not import concrete agent or runtime implementations.
Agent must not construct concrete stores, indexes, or providers implicitly.
Product packages must not import `bijux-canon-dev`. Canonical packages must not
shell out to sibling package commands or guess package-root callables.

Cross-package data moves through versioned, canonically serialized artifacts or
explicit ports. Source, document, chunk, corpus snapshot, model lock, index
generation, retrieval execution, evidence packet, claim graph, agent execution,
runtime run, attempt, and publication identities remain distinct across those
handoffs. CLI and HTTP adapters call the same application service and do not
own domain verdicts.

## Compatibility Ownership

Compatibility ownership is explicit and versioned:

| Compatibility distribution | Canonical owner |
| --- | --- |
| `bijux-canon` | `bijux-canon-runtime` |
| `agentic-flows` | `bijux-canon-runtime` |
| `bijux-agent` | `bijux-canon-agent` |
| `bijux-rag` | `bijux-canon-ingest` |
| `bijux-rar` | `bijux-canon-reason` |
| `bijux-vex` | `bijux-canon-index` |

The historical name does not move authority. In particular, `bijux-rag`
continues to preserve the v1 ingest surface; new answer and research
composition belongs to reason through runtime. A compatibility bridge delegates
arguments, objects, exceptions, exit status, and version truth to its canonical
owner. Translation requires a separately versioned adapter contract.

## Caller Migration Inventory

The current source and distribution inventory identifies the following callers
that cross the intended boundary. This is the complete migration queue for the
audited tree; future violations are rejected by regenerated import and caller
inventories.

| Current callers | Boundary problem | Required destination |
| --- | --- | --- |
| `packages/bijux-canon-runtime/tests/regression/test_adversarial_guards.py` | canonical runtime test imports compatibility alias `bijux_rag` | import the versioned `bijux_canon_ingest` contract or exercise the alias only from compatibility-package tests |
| `packages/bijux-canon-runtime/tests/regression/test_budget_semantics.py` | canonical runtime test imports compatibility alias `bijux_rag` | import the versioned `bijux_canon_ingest` contract or an explicit runtime port |
| `packages/bijux-canon-runtime/tests/regression/test_hostile_artifact_store.py` | canonical runtime test imports compatibility alias `bijux_rag` | import the versioned `bijux_canon_ingest` contract or an explicit runtime port |
| `packages/bijux-canon-runtime/tests/regression/test_long_horizon_flow.py` | canonical runtime test imports compatibility alias `bijux_rag` | import the versioned `bijux_canon_ingest` contract or an explicit runtime port |
| `packages/bijux-canon-runtime/tests/regression/test_replay_across_process_boundary.py` | canonical runtime test imports compatibility alias `bijux_rag` | import the versioned `bijux_canon_ingest` contract or an explicit runtime port |

Existing compatibility-package modules and entrypoints are not migration
violations: delegation is their sole responsibility. Imports within a canonical
package are likewise internal ownership edges. Documentation, examples, shell
automation, and workflows that mention preserved names must use them only when
teaching or testing compatibility; new canonical examples use canonical names.

## Enforcement And Completion

Ownership is closed only when all of the following are true:

1. The generated distribution and caller inventory covers every workspace
   distribution, public entrypoint, and Python source file.
2. Forbidden import, sibling shell-out, duplicate-schema, and transport-domain
   checks fail closed in CI.
3. Each listed caller has moved to its canonical contract or an explicit port,
   while installed compatibility tests continue to prove v1 identity and
   command parity.
4. Built wheels install outside the source tree with no undeclared sibling
   dependency, and the composed flow uses those installed distributions.
5. Focused success, failure, boundary, restart, and network-disabled replay
   checks preserve artifact identity and owner-produced verdicts.

Until those conditions hold, this document is authoritative about the target
boundary, while the caller table is an explicit migration queue rather than a
claim that the source tree has already reached the target.
