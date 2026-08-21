---
title: Production Threat Model
audience: mixed
type: reference
status: canonical
owner: bijux-canon-docs
last_reviewed: 2026-08-21
---

# Production Threat Model

Bijux Canon treats source documents, retrieved passages, provider responses,
serialized artifacts, indexes, databases, network peers, and package inputs as
untrusted. Content may be retained and cited as evidence; it never receives
authority to change policy, tools, corpus scope, filters, schemas, secrets,
endpoints, budgets, or citation rules.

This model covers the supported local, single-node production profile. It does
not claim tenant isolation, distributed consensus, managed high availability,
or a safe boundary between mutually hostile users in one operating-system
account.

## Assets And Security Objectives

| Asset | Security objective |
| --- | --- |
| source bytes and exact locators | preserve integrity, provenance, lawful access, and disclosure policy |
| corpus snapshots and truth labels | prevent substitution, split leakage, silent relabeling, and mixed generations |
| model and index generations | bind dimensions, normalization, model assets, parameters, and source snapshot before use |
| evidence packets, claims, citations, and traces | preserve causal linkage and fail closed on missing or altered payloads |
| runtime jobs, CAS payloads, and DuckDB state | provide atomic state transitions, restart recovery, cancellation, and tamper detection |
| policy, budgets, tools, and provider configuration | prevent document or provider content from escalating authority |
| credentials and sensitive source content | prevent serialization, logging, error, artifact, metric, or response disclosure |
| installed wheels, lock files, SBOMs, and provenance | prevent dependency or build substitution and retain reproducible release identity |

Availability is bounded rather than absolute. The service must reject work that
exceeds declared limits without corrupting the last accepted corpus, index, or
runtime generation.

## Trust Boundaries

```text
untrusted files and archives -> ingest validation -> immutable corpus snapshot
untrusted retrieved text     -> reason evidence boundary -> claims and citations
untrusted provider output    -> typed provider adapter -> validated result
installed package ports      -> runtime composition root -> durable run state
local or remote client       -> CLI/HTTP adapter -> shared application service
artifact or database bytes   -> integrity checks -> admitted persisted state
dependency and model sources -> lock/provenance checks -> installed execution
```

CLI and HTTP adapters are authority boundaries, not alternate implementations.
They validate authentication and request limits supplied by the deployment,
then invoke the same application services. Runtime composes package ports and
persists decisions; it does not weaken the owning package's validation.

## Threats, Controls, And Required Proof

| Threat | Required controls | Required proof and owner |
| --- | --- | --- |
| prompt injection in documents or retrieved passages | mark content as data; use fixed typed tool/provider ports; prohibit content-derived policy, endpoints, filters, schemas, budgets, and citation rules; retain the injection text as inspectable evidence | adversarial passages attempt each authority change and produce unchanged effective policy plus explicit refusal; reason and agent owners |
| provider response injection or malformed structured output | validate against a closed schema; reject extra fields, tool requests, URLs, instructions, and oversized output; never execute returned text | malformed, recursive, oversized, and authority-seeking provider responses fail before state mutation; adapter and reason owners |
| path traversal, symlink races, device files, and root escape | resolve against an approved root, reject absolute and parent traversal, inspect file type, avoid following unsafe links, open with race-resistant semantics where supported, and retain the resolved identity | traversal, symlink swap, FIFO/device, case and Unicode boundary tests fail without reads or writes outside the approved root; ingest and runtime owners |
| archive, XML, document, or parser bomb | preflight compressed and expanded bytes, members, nesting, pages, nodes, text, time, memory, and chunks; disable external entities and network resolution; isolate expensive parsers | boundary and over-limit inputs terminate with typed failures; fuzzing retains minimized reproducers and resource observations; ingest owner |
| unsafe encoding or malformed structure | detect or require encoding, bound replacement, validate structure before allocation, and distinguish unsupported, malformed, encrypted, and OCR-required input | real and malformed samples for each supported format exercise deterministic success and refusal; ingest owner |
| unapproved network or provider access | lazy credential resolution; approved HTTPS origins, certificate verification, DNS and redirect policy, connection and response limits, bounded retry, and offline denial | offline workflows run with network disabled; disallowed schemes, redirects, hosts, timeouts, response types, and retries fail closed; package adapter and runtime owners |
| secret or sensitive-evidence disclosure | use secret references instead of values; redact structured logs, errors, traces, metrics, subprocess environments, and HTTP responses; enforce field-level source disclosure policy | seeded canaries in credentials and source text are absent from every retained and returned surface except an explicitly authorized evidence payload; all owners |
| artifact, index, event, or database tampering | bind canonical payload hashes, schemas, producer versions, causal/event chains, source/model/config identities, and commit/finalization markers; use atomic publication and preserve the last good generation | bit flips, truncation, reordering, substitution, missing payloads, dimension mismatch, and rollback attempts refuse load/replay while retaining forensic identity; index, reason, agent, and runtime owners |
| denial of service and resource exhaustion | bound source bytes, chunks, vectors, candidates, tokens, steps, jobs, queues, responses, artifacts, connections, retries, time, disk, and worker concurrency; apply backpressure and cancellation | exact-boundary and over-boundary tests demonstrate deterministic rejection, bounded cleanup, and continued health of an unrelated job; all product owners |
| multi-process races and stale state | database transactions, unique/idempotency keys, compare-and-swap or equivalent generation checks, leases with expiry, atomic files, startup recovery, and single-writer rules where required | competing processes, crash points, retry, cancellation, and restart preserve one legal transition history with no partial generation publication; runtime and index owners |
| dependency, model, build, or release substitution | frozen dependency and model identities, hash-checked acquisition, built-wheel tests outside the source tree, fatal vulnerability audits, SBOMs, signed provenance where available, pinned workflow actions, and immutable release versions | lock drift, audit findings, changed model bytes, wheel metadata mismatch, source-tree imports, missing SBOM, and release digest mismatch are fatal; dev and release owners |
| evidence disclosure through citations, diagnostics, or exports | authorize source and locator access independently of answer access; minimize excerpts; classify exports; protect corpus and truth paths; log identities rather than content | unauthorized citation resolution, inspect, export, and error paths reveal no source bytes while authorized exact-span resolution remains hash-bound; reason and runtime owners |

Passing a unit test with a mock payload is not production proof. Admission uses
installed distributions, real lawful documents where the threat applies,
malformed and adversarial cases, process restart where state is involved, and
the same storage and transport path as the supported profile.

## Prompt And Tool Authority

The effective research policy is constructed before untrusted text enters the
reason or agent boundary. Tools are registered by code and deployment policy,
not by names in a document. Every tool call is checked against the declared
operation, corpus snapshot, filters, budget, and argument schema. Retrieved text
cannot introduce a tool, change its endpoint, expand its root, request secrets,
or suppress citation and counterevidence requirements.

Provider adapters return typed candidate data. The agent records why a call was
allowed, the bounded arguments, tool identity, start and terminal event, result
artifact identity, and remaining budget. Unsupported authority requests become
inspectable findings, not hidden prompt text.

## Files, Parsers, And Archives

Input discovery separates metadata inspection from content parsing. An approved
root and file policy govern both. Archive admission validates every member name
before extraction, rejects links and special files, prevents duplicate or
case-colliding destinations, and enforces aggregate expanded-size and member
limits. Parsers do not resolve external XML entities, remote stylesheets,
linked resources, macros, or embedded executables.

Parser fuzzing records the seed, parser and dependency versions, limits,
failure class, and minimized reproducer hash. A crash, timeout, memory breach,
or nondeterministic result is a failed parser qualification even if a retry
succeeds.

## Network And Credential Boundary

Offline help, inspect, replay, lexical retrieval, and supported local workflows
resolve no provider credential and perform no network request. A selected
remote provider resolves only its named secret reference at call time. Secret
values never enter canonical configuration, run manifests, events, exception
messages, cache keys, or artifacts.

Remote requests enforce TLS, approved origins, redirect count and target
policy, connect/read/total timeouts, response media and byte limits, bounded
retries for classified transient failures, and circuit breaking. Response
content is untrusted regardless of TLS success.

## Persistence And Multi-Process Safety

CAS accepts payload bytes before references become visible and verifies the
payload digest on every load used for replay or publication. DuckDB state
changes use transactions and legal transition predicates. A job attempt has a
stable identity distinct from its process and records idempotency, lease,
heartbeat, cancellation, and terminal status.

Crash recovery scans incomplete attempts, verifies referenced payloads, and
either resumes through a recorded transition or marks a typed failure. It never
promotes a directory, index, or run merely because files are present. Backup
and restore proof includes restored hashes, database integrity, CAS
reachability, index generation load, inspect, and offline replay.

## Supply Chain And Release

Required static analysis, dependency audit, SBOM generation and validation,
workflow pin checks, wheel metadata inspection, installed-family tests, and
provenance checks are fatal gates. A suppression identifies the finding, owner,
reason, narrow path and rule, compensating control, approval, and expiry.
Unowned, broad, or expired suppressions fail the gate.

Release artifacts are immutable and content-addressed. A published version is
never replaced with different bytes. Base images and workflow actions use
immutable digests; the supported container runs as non-root, declares writable
volumes, uses a read-only root filesystem where practical, handles termination
gracefully, and distinguishes liveness from dependency-aware readiness.

## Observability And Incident Response

Structured telemetry exposes request and job counts, typed failures, latency,
queue and worker saturation, retry and breaker state, cache behavior, corpus
and index generations, artifact integrity, storage health, and replay outcomes.
It excludes secrets and source content by default. Suggested alerts and SLOs
must be derived from retained measurements rather than aspirational numbers.

An incident record preserves affected identities, last good generation,
rejected or quarantined material, detection and containment decisions, scope,
recovery checks, and disclosure review. Recovery follows an executed runbook;
documentation alone does not prove backup, corruption, or incident readiness.

## Residual Risk And Deployment Duties

The local profile relies on operating-system account isolation, filesystem and
network controls, secret management, TLS trust, host patching, backups, and
monitoring supplied by the deployment. Optional native libraries and document
parsers increase the supply-chain and memory-safety surface. Provider services
can retain prompts or evidence according to their own terms.

Operators must grant least-privilege read, write, network, and secret access;
separate sensitive corpora; configure retention; review provider disclosure;
and run denial, corruption, restart, backup, and restore exercises for the
enabled boundaries. A boundary not exercised is not a supported production
claim.
