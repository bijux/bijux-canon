---
title: Public Authority Claims
audience: mixed
type: reference
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Public Authority Claims

Runtime claims name the authority and retained boundary under which they hold.
Governed, verified, finalized, resumable, deterministic, and replayable are
separate properties.

```mermaid
flowchart LR
    authority[Declared authority]
    execution[Mode-specific execution]
    decision[Verification and arbitration]
    persistence[Finalized persistence]
    comparison[Replay comparison]
    claim[Bounded public claim]

    authority --> execution --> decision --> persistence --> comparison --> claim
```

## Claim vocabulary

| Public wording | Evidence required | Bound on the claim |
| --- | --- | --- |
| resolved flow | semantically valid manifest, dependency order, identities, and immutable plan | has not necessarily been authorized to execute |
| governed live run | live mode, required policy, authorized effects, complete verification coverage, and finalized trace | covers recorded integrations and declared rules |
| unsafe run | explicit unsafe mode, semantic warning, relaxed policy, and finalized trace | is not equivalent to governed live execution |
| verified result | complete registered findings and recorded arbitration policy/decision | does not establish factual or scientific truth |
| finalized run | consistent trace, events, artifacts, evidence, entropy, and terminal store state | external payload durability remains deployment-owned |
| resumable run | compatible authority, checkpoint, indices, effect state, and store identity | cannot make an unrecorded external effect transactional |
| deterministic execution | declared strict boundary, controlled entropy, and matching identity | cannot control omitted providers, hardware, clocks, or mutable data |
| acceptable replay | original envelope and policy judge retained differences inside declared bounds | acceptable drift remains drift and requires domain judgment |

## Mode and endpoint language

Examples name the selected mode and its authority. `dry-run` is simulation,
`observe` depends on supplied observations, and `unsafe` retains an explicit
non-equivalent classification.

The HTTP schema describes request and response contracts. Health and readiness
are implemented; flow run and replay currently return `501 Not Implemented`.
Schema validation is not described as execution availability.

See [invariants](invariants.md) for machine-enforced authority laws and
[risk register](risk-register.md) for persistent effect and deployment risks.
