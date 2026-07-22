---
title: Runtime Handbook
audience: mixed
type: index
status: canonical
owner: bijux-canon-runtime-docs
last_reviewed: 2026-07-21
---

# Runtime Handbook

`bijux-canon-runtime` is the authority that resolves a `FlowManifest`, checks
dataset and dependency state, plans ordered execution, enforces budgets and
verification gates, records causally ordered events, and decides whether a run
may be persisted or accepted for replay.

A completed lower-layer call is not automatically a valid runtime step. The
runtime distinguishes execution failure from verification failure, records
authority and human interventions, and binds replay to the original flow,
dataset, policy, environment, plan, artifact, and entropy identities.

```mermaid
flowchart LR
    manifest["FlowManifest"]
    resolve["resolve datasets + contracts"]
    plan["immutable ExecutionPlan"]
    execute["budgeted step execution"]
    verify["verification arbitration"]
    persist["trace + artifacts + run record"]
    replay["replay verdict + diff"]

    manifest --> resolve --> plan --> execute --> verify --> persist --> replay
    verify -. rejection .-> replay
```

## Manifest Authority

| Manifest field | Runtime decision |
| --- | --- |
| flow, tenant, state, agents, dependencies | who owns the run and which order is valid |
| dataset descriptor and deprecation policy | whether the exact data identity is admissible |
| retrieval contracts and verification gates | which lower-layer evidence and checks are mandatory |
| determinism level and nondeterminism intent | which variability is declared rather than accidental |
| entropy budget and allowed variance | how much uncertainty the run may consume |
| replay envelope, mode, and acceptability | which future execution can count as a replay |

`FlowManifest` is structural; semantic validity is enforced during resolution,
planning, authority checks, execution, verification, and replay. Constructing
the dataclass alone does not prove that a flow is executable.

## Run Modes

- `plan` resolves and plans without executing steps
- `dry-run` exercises runtime preparation without live side effects
- `live` executes under declared policy and records the run
- `observe` captures evidence without granting normal execution authority
- `unsafe` is an explicit reduced-guarantee mode, not an alias for live

Plan and dry-run deliberately avoid lower-package intelligence, and observe
evaluates a supplied run. Success in those modes does not establish that the
live agent, retrieval, vector-contract, and reasoning adapters are callable.

## Live Composition Status

```mermaid
flowchart TD
    executor["runtime step executor"] --> loader["integration loader"]
    loader --> adapter["domain-aware adapter required"]
    adapter --> package["canonical package contract"]
    adapter --> record["runtime record"]
    package --> adapter
```

The current loaders ask package roots for four callables:

| Step boundary | Callable expected by runtime | Current status |
| --- | --- | --- |
| agent | `bijux_canon_agent.run` | absent; agent exposes a pipeline-and-trace contract |
| retrieval | `bijux_canon_ingest.retrieve` | absent at the root; the application retrieval signature and output model differ |
| vector enforcement | `bijux_canon_index.enforce_contract` | absent; index owns a richer request, capability, provenance, and refusal contract |
| reasoning | `bijux_canon_reason.reason` returning runtime `ReasoningBundle` | absent; reason owns different claim, support, trace, and verification models |

Compatibility import roots mirror canonical behavior and do not repair these
seams. This means the package can plan flows, produce dry-run records, observe
supplied results, and exercise runtime-local policy and storage behavior, while
a canonical live flow that reaches these loaders is not currently an
established end-to-end path.

The durable proof is an installed-package integration test, not an import
check. It must execute the loaders and demonstrate that source, evidence,
contract, claim, trace, artifact, and failure identities survive conversion
into runtime-owned records. Until then, live CLI examples describe the runtime
interface and required policy posture rather than a turnkey composition of all
canonical packages.

## Follow One Governed Run

```mermaid
stateDiagram-v2
    [*] --> Resolved: manifest + policy
    Resolved --> Planned: contracts and identities valid
    Planned --> Completed: executable mode
    Planned --> [*]: plan mode
    Completed --> Finalized: trace and semantics valid
    Finalized --> Accepted: policy accepts
    Finalized --> Rejected: policy refuses
    Finalized --> NonCertifiable: evidence is insufficient
    Accepted --> Replayed: retained envelope compared
```

Plan mode stops after resolution and returns no run identifier or trace. Other
modes require an execution store and the resources appropriate to their
authority. A finalized trace can describe a rejected or non-certifiable run;
finalization means the record is closed, not that policy accepted it.

## Read A Runtime Result

| Record | Question it answers | Failure if absent or inconsistent |
| --- | --- | --- |
| manifest and resolved plan | what was authorized, ordered, and fingerprinted? | the run has no stable execution contract |
| dataset descriptor | which exact data state was admissible? | dataset drift cannot be distinguished from replay drift |
| authority and verification policy | who permitted effects and how findings were arbitrated? | completion can be mistaken for acceptance |
| event trace and checkpoints | what happened, in which causal order? | resume and failure analysis become speculative |
| artifacts, evidence, claims, and tool calls | what the run consumed and produced | outputs lose lineage |
| entropy use and replay envelope | which variance was declared and retained? | determinism claims exceed captured evidence |
| replay verdict and diff | whether a later run satisfies the original policy | similar final content can be mislabeled equivalent |

## Do Not Collapse Runtime States

Execution, finalization, acceptance, and replay are separate decisions:

| State | What may be claimed | What may not be claimed |
| --- | --- | --- |
| executed | declared steps returned outcomes | verification passed or the run is complete |
| finalized | the trace and required records were closed | policy accepted the run |
| accepted | arbitration admitted the finalized record under its policy | the result is universally correct |
| non-certifiable | retained evidence cannot support the requested guarantee | the run necessarily failed to produce useful observations |
| replay acceptable | the comparison satisfied the original replay policy | the two executions were bitwise identical unless exactness was required and established |
| replay unacceptable | a disallowed difference or identity mismatch was found | every output from the later execution is false |

This vocabulary prevents a common integrity failure: promoting “the command
finished” into “the run is valid.” Persist the status, arbitration evidence,
certifiability, and replay verdict independently so downstream systems cannot
infer a stronger state from a weaker one.

## Runtime Trust Boundary

Runtime governs lower-package results; it does not recreate them. Ingest owns
source preparation, index owns vector execution, reason owns claim/evidence
semantics, and agent owns role lifecycle. Runtime binds their governed outputs
to authority, policy, persistence, and replay.

The DuckDB execution store retains causal run state and supports inspection,
resume, and replay. It is a single-writer local store, not a transaction manager
for external tools. A database commit cannot undo a provider call or filesystem
write; live integrations need idempotency or compensation beyond the store.

Its schema retains run and dataset identity, steps, event payloads,
checkpoints, artifact and evidence metadata, entropy use, tool invocations,
claim identifiers, a verification-policy fingerprint, and the run-level
arbitration decision. Artifact content and evidence content are not stored in
those metadata rows. Per-engine verification results and replay analysis also
do not have dedicated tables. Operators must retain external content by hash
and must not infer payload availability or full verification detail from the
presence of a run row.

## Evidence And Limits

| Claim | Evidence to inspect | Limit |
| --- | --- | --- |
| a run was accepted | finalized trace, verification results, arbitration decision, certifiability | acceptance is only under the declared policy |
| resume preserved authority | tenant, manifest, plan, dataset, policy, checkpoint, store identity | changed authority requires a new run |
| replay is exact | original envelope, retained inputs, event and artifact identity, zero disallowed diff | cannot control state never captured |
| bounded replay is acceptable | original allowed variance and evaluated semantic diff | tolerance cannot be invented after divergence |
| storage is complete | schema contract, finalized records, external artifact availability | metadata does not guarantee payload retention |
| live composition works | installed loader execution plus cross-package identity and failure assertions | dependency resolution, plan mode, or dry-run success |

The [entrypoint examples](interfaces/entrypoints-and-examples.md) begin with
plan mode, then show persisted execution, inspection, replay, and diff. The v1
HTTP application currently implements health and readiness; run and replay
requests return `501 Not Implemented`.

## Continue By Question

| Question | Next page |
| --- | --- |
| why is runtime the final execution authority? | [Foundation](foundation/index.md) |
| how do planning, execution, verification, storage, and replay connect? | [Architecture](architecture/index.md) |
| which Python, CLI, HTTP, configuration, and artifact contracts are callable? | [Interfaces](interfaces/index.md) |
| how do I operate, inspect, resume, replay, secure, or recover a run? | [Operations](operations/index.md) |
| which invariants defend authority, persistence, entropy, and replay? | [Quality](quality/index.md) |

## Replay Is A Verdict

Replay analysis can accept, reject, or qualify a comparison based on policy,
dataset evolution, environment, entropy, event order, verification results,
and stored-envelope identity. A replay mismatch remains a mismatch even when
the new run produces superficially similar content.
