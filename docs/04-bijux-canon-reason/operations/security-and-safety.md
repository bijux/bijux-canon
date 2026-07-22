---
title: Security and Safety
audience: mixed
type: how-to
status: canonical
owner: bijux-canon-reason-docs
last_reviewed: 2026-07-22
---

# Security and Safety

Treat specifications, corpora, traces, and evidence files as untrusted input.
The package can read a configured corpus and write an auditable run tree, but it
does not provide a sandbox, scientific peer review, or a production identity
system.

## Evidence integrity boundary

```mermaid
flowchart LR
    A[Corpus bytes] -->|SHA-256| B[Pinned provenance]
    B --> C[Evidence record]
    C --> D[Claim support span]
    D --> E[Verification]
    E --> F{Path inside run root?}
    E --> G{Artifact digest matches?}
    E --> H{Byte span and snippet digest match?}
```

Evidence verification resolves each recorded content path beneath the supplied
artifact root and rejects paths that escape it. It then checks the evidence
file digest, the exact byte range used by a support, and that range's SHA-256
digest. The run manifest covers the core run files and discovered provenance
files.

These checks establish traceability and tamper evidence. They do not establish
source reliability, causal validity, or the truth of a generated conclusion.
Those remain review responsibilities for the domain using the package.

## Operating controls

- Place the artifact root on a filesystem with permissions appropriate for the
  specifications, corpus snapshots, and evidence it contains.
- Pin corpus inputs. A mutable path can resolve to different bytes on a later
  run even when its filename is unchanged.
- Set `RAR_RETRIEVAL_CORPUS_MAX_BYTES` before loading externally supplied
  corpora. Set disk, elapsed-time, and CPU budgets for shared environments.
- Do not treat the elapsed-time or CPU settings as kill switches: the current
  implementation checks them after execution returns.
- Keep run manifests and fingerprints with exported artifacts. Verification
  without the artifact directory skips file-backed evidence checks.
- Avoid placing credentials or private tokens in specifications, corpus text,
  tool results, or metadata because those values can become durable artifacts.

## HTTP deployment boundary

The API rejects declared request bodies larger than 8 KiB, XML media types,
item responses larger than 2 MiB, offsets above 1,000,000, and list responses
above 100 items. The request-size guard depends on `Content-Length`; deploy a
reverse proxy or ASGI server with an independently enforced body limit when
clients are not trusted.

Authentication is optional. When `RAR_API_TOKEN` is unset, the application
accepts requests without credentials. When it is set, clients must send the
exact value in `x-api-token`. This shared-token mechanism does not provide
users, roles, tenant isolation, token rotation, or transport encryption.

`RAR_API_RATE_LIMIT` enables an in-process counter keyed by the supplied token
or by the anonymous bucket. The default is disabled, and state is neither
distributed nor durable. Put externally reachable deployments behind TLS,
strong identity and authorization, network-level request limits, and durable
observability.

## Investigate a disputed claim from bytes outward

Do not begin with the generated conclusion. Establish custody in this order:

```mermaid
flowchart LR
    manifest["manifested file identity"]
    file["evidence file digest"]
    span["byte range + span digest"]
    support["claim-support edge"]
    check["check + finding"]
    status["claim status"]
    trace["reasoning trace"]

    manifest --> file --> span --> support --> check --> status --> trace
```

1. verify the manifest and locate the evidence file beneath the authorized
   artifact root;
2. recompute the file digest, byte bounds, exact span digest, and cited bytes;
3. confirm that the support edge names that evidence and the intended claim;
4. replay applicable checks from retained inputs without calling live external
   services;
5. derive the claim status from findings and policy; and
6. compare the derived status and evidence identities with the trace and
   exported report.

Stop at the first broken link. A later artifact cannot repair earlier custody,
and a matching final sentence cannot substitute for a changed evidence byte.

## Security regression matrix

| Mutation or attack | Required behavior |
| --- | --- |
| evidence path escapes the run root through traversal or a resolved link | refusal before reading or disclosing the target |
| evidence file changes after the manifest is written | file-digest failure that identifies the affected record |
| support keeps the same offset while the cited bytes change | span/snippet digest failure; claim is not treated as supported |
| a core run file is removed or replaced by a file from another run | manifest or run-identity failure, not partial verification success |
| verification runs without the governed artifact directory | explicit evidence-check limitation; no file-backed integrity claim |
| mandatory check is unavailable, raises, or returns contradictory findings | visible unavailable/failure disposition under the selected policy |
| replay attempts a fresh provider or retriever call | refusal or a clearly separate new execution, never frozen replay |
| API body omits `Content-Length` or exceeds downstream resource capacity | enclosing proxy/server enforces byte and resource limits independently |
| shared token, corpus text, or tool output reaches an error/log artifact | disclosure incident; rotate credentials where applicable and protect the run tree |

Preserve the disputed run tree read-only, record who obtained access, and work
from a copy when investigation tooling could alter timestamps or files. A
digest can prove that bytes differ; it cannot recover deleted evidence or
decide whether the source was trustworthy.

## Safe interpretation

A clean verification report means the trace satisfied the implemented
structural and provenance invariants under the chosen policy. Always retain the
policy, specification, runtime descriptor, and source evidence when a decision
depends on that result.
