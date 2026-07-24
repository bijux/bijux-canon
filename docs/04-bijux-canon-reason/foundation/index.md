---
title: Foundation
audience: mixed
type: index
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-22
---

# Foundation

`bijux-canon-reason` converts a declared problem and evidence set into an
inspectable reasoning record. It plans the work, records tool and evidence
events, emits typed claims, verifies structural and grounding invariants, and
packages the result as a content-addressed run.

## Reasoning boundary

```mermaid
flowchart LR
    retrieval["retrieved or pinned evidence"]
    spec["ProblemSpec"]
    reason["plan, execute, claim, verify"]
    bundle["manifested reasoning run"]
    reviewer["caller or reviewer"]
    agent["agent workflow"]
    runtime["runtime executor"]

    retrieval --> reason
    spec --> reason --> bundle
    bundle --> reviewer
    agent -. explicit adapter required .-> reason
    runtime -. missing root adapter .-> reason
```

The package owns interpretation records, not universal truth. Retrieval order
and backend scoring remain index concerns. Multi-call scheduling and provider
policy remain agent concerns. Acceptance of an end-to-end workflow remains a
runtime concern.

The dashed links do not claim direct composition. Agent does not depend on the
reason package, and runtime currently requests a root-level `reason` callable
returning a runtime-owned bundle that the reason root does not export. A host
adapter must preserve problem, evidence, support, claim, trace, verification,
and manifest identity before either higher boundary can claim custody.

## Claim contract

| Dimension | Values or content | Review value |
| --- | --- | --- |
| kind | observed, assumed, derived | distinguishes source facts from premises and inference |
| status | proposed, validated, rejected | prevents proposal from being mistaken for accepted output |
| support | claim, evidence, or tool reference with exact span and snippet digest | makes grounding byte-inspectable |
| confidence | bounded assessment supplied with the claim | records judgment without substituting for support |
| identity | content-derived claim reference | reveals contract changes rather than reusing identity |

A reference to a document is not sufficient grounding. A support record binds
the claim to exact bytes and a SHA-256 digest so the verifier can distinguish a
stable source span from a nearby or replaced passage.

## Read a claim as four decisions

| Decision | Owning record | Valid question | Invalid shortcut |
| --- | --- | --- | --- |
| evidence admission | `EvidenceRef`, source digest and retrieval provenance | which exact bytes were available to reasoning? | treating a document label as retained evidence |
| support | `SupportRef`, exact span and snippet digest | which bytes are asserted to support this claim? | accepting a nearby citation or score as support |
| inference | claim kind, derivation/tool trace and dependencies | how did observed or assumed material become this conclusion? | treating fluent prose or confidence as a derivation |
| disposition | claim status and verification findings | why is the claim proposed, validated, rejected, or insufficient? | treating process completion as validation |

These decisions remain separately inspectable so a reviewer can accept the
evidence identity while rejecting the inference, or accept a well-formed run
whose honest outcome is insufficient evidence.

## Verification meaning

A passing verification report means the registered structural, provenance,
hash, support, tool, and replay invariants passed over the retained record. It
does not prove source authority, corpus completeness, calibrated confidence,
absence of counterevidence, or real-world truth. `insufficient_evidence` is an
explicit controlled outcome and must not be rewritten as an execution error.

## Reference execution

The bundled reasoner is extractive. The local retrieval path uses BM25 over a
pinned corpus; the alternative default runtime is deterministic and local.
These paths provide a reproducible reference implementation, not a claim of
general reasoning or state-of-the-art search.

## Read by question

| Question | Guide |
| --- | --- |
| What stable problem does the package solve? | [Package overview](package-overview.md) |
| Which responsibilities are excluded? | [Scope and non-goals](scope-and-non-goals.md) |
| Where do index, reason, agent, and runtime authority meet? | [Ownership boundary](ownership-boundary.md) and [Repository fit](repository-fit.md) |
| Which planning, evidence, claim, and verification capabilities exist? | [Capability map](capability-map.md) |
| How does a problem become a complete run? | [Lifecycle overview](lifecycle-overview.md) |
| What do support, trace, fingerprint, and replay mean? | [Domain language](domain-language.md) |
| Which changes preserve reviewability? | [Change principles](change-principles.md) |
| Which adjacent systems can alter evidence or execution? | [Dependencies and adjacencies](dependencies-and-adjacencies.md) |
