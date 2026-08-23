---
title: Security and Safety
audience: mixed
type: explanation
status: canonical
owner: bijux-canon-index-docs
last_reviewed: 2026-08-24
---

# Security and Safety

Index can ingest documents and vectors, load plugins, connect to vector stores,
persist run artifacts, and expose results over HTTP. Its execution contracts
govern retrieval semantics; deployment security still belongs to the hosting
application and backend configuration.

## Authority map

```mermaid
flowchart LR
    A[Client request] --> B[request validation]
    B --> C[authorization policy]
    C --> D[budget and capability gates]
    D --> E[embedding or vector-store adapter]
    E --> F[artifact and run stores]
    F --> G[explain, replay, and compare]
    H[plugin registry] --> E
```

## Authorization posture

The runtime bootstrap supports allow-all and deny-all authorization modes. The
default is allow-all unless `BIJUX_CANON_INDEX_AUTHZ_MODE` selects `deny` or
`deny_all`. That switch is a package policy primitive, not user authentication
or tenant isolation. A network deployment must provide identity, per-operation
authorization, transport security, and audit controls outside the package.

Canonical generation queries can additionally carry a content-addressed
`RetrievalAuthorizationScope`. It names the admitted generation and allowed
source or path identities. Index intersects that authority with the caller's
metadata filter before the result limit on lexical, exact-dense, and ANN
backends. A disjoint source request becomes a scope-bound empty result, while a
generation outside the declared authority is denied. The effective filter and
authorization identity must remain identical through fusion, reranking, and
citation resolution; mixed lineage is refused rather than merged.

Read-only mode can prevent mutation at configured boundaries. Enable it for
inspection and replay consumers that do not need corpus or artifact writes.

## Backend and credential safety

- Keep vector-store and embedding credentials in an approved secret mechanism,
  not in configuration files, URIs, traces, or command history.
- Pin backend, embedding provider, model, plugin, and protocol versions.
- Restrict state, cache, run, and artifact paths to the service identity.
- Treat imported corpus, index, artifact, and run files as untrusted until
  schema, fingerprint, dimensions, and ownership are validated.
- Review consistency and transaction semantics before claiming atomic ingest
  or replay equivalence across a remote backend.

Lineage records a redacted backend URI. If a custom adapter returns raw
credentials in metadata, that adapter violates the provenance boundary.

## Plugin execution

Plugins execute Python code in the index process. Install only reviewed,
pinned plugins from a controlled source. Registry discovery is not a sandbox,
and a timeout limits duration rather than filesystem, network, or process
authority. Run untrusted extensions in an isolated service boundary.

Plugin load failures, call timeouts, backend capability failures, and backend
unavailability remain separate so operators do not retry a malicious or
incompatible plugin as if it were a transient network fault.

## Resource and denial-of-service controls

Set ingest vector limits, maximum `top_k`, query-size limits, execution time,
memory, distance computations, ANN probes, candidate pool, index memory, and
search bounds. Approximate on-demand index construction can be substantially
more expensive than querying a prepared index; authorize and budget it
separately.

Low-signal refusal prevents weak approximate results from being presented as
useful neighbors. Witness sampling detects quality loss but consumes exact-work
budget. Neither control replaces application-level request quotas.

## Artifact and replay integrity

Run records use atomic file replacement, but filesystem atomicity does not
prove trusted origin. Protect artifact and run directories from cross-tenant
read/write access and retain fingerprints, plan identity, backend metadata,
and randomness declarations.

Replay must refuse changed indexes, parameters, or non-replayable randomness
when strict comparison is requested. Never weaken a replay refusal to make an
operational dashboard green; retain the refusal as the accurate safety result.

## Exercise the hostile path

The security review should include observed denials and degraded backend
behavior, not only configuration inspection:

| Mutation or attack | Required behavior | Evidence to preserve |
| --- | --- | --- |
| unauthenticated caller reaches an allow-all bootstrap | enclosing service denies access before index authorization is treated as sufficient | principal, operation, outer decision, and package decision |
| request exceeds `top_k`, vector, candidate, probe, time, or distance budget | refusal before unbounded work; no partial result presented as complete | requested/allowed budget, consumed work, and typed failure |
| corpus or vector belongs to another tenant | no read, mutation, provenance disclosure, or cache reuse across the boundary | tenant/scope identities and denial record without sensitive payload |
| backend URI contains credentials | provenance contains a usable redacted identity and no secret | raw source classification, redacted value, and leak check |
| native index is truncated, forged, or dimensionally inconsistent | load/query refusal before authoritative result production | artifact fingerprint and failed schema/native invariant |
| remote mutation times out after dispatch | explicit unknown outcome with idempotency, reconciliation, or refusal | operation identity, attempts, service response, and reconciliation result |
| plugin raises, blocks, or returns malformed data | isolated typed plugin failure; no retry as a transient backend outage | plugin identity, call boundary, timeout/error, and rejected output class |
| approximate backend returns low-signal neighbors | declared refusal or degraded result with witness/quality evidence | threshold, observed quality, candidate set, and decision |
| replay points at changed state or parameters | blocking mismatch with original and observed identities | replay envelope, semantic diff, verdict, and reason |

## Preserve an incident-grade retrieval record

For a disputed or suspicious result, retain the validated request, caller and
tenant scope, authorization and read-only decisions, budget, execution plan,
adapter/plugin identity, redacted service identity, index and corpus
fingerprints, randomness declaration, ranked result, provenance, retries,
failure classifications, and replay comparison. Preserve native or remote
snapshots only when authorization and retention policy allow it.

Containment must not erase the evidence needed to explain the result. Disable
the affected backend or plugin, prevent new mutations, protect the relevant
run/artifact records from modification, and compare against an exact or known-
good backend before deciding whether prior results remain admissible.
