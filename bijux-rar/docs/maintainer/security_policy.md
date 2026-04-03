STATUS: AUTHORITATIVE

# Security

This document defines the **explicit security model and threat boundaries** of bijux-rar.

Security properties outside this document are **not guaranteed**.

Report vulnerabilities **privately** via GitHub Security Advisories.  
Do not open public issues for security concerns.

---

## Security posture

bijux-rar is designed as a **deterministic execution and verification engine**, not a hardened multi-tenant service.

Security controls are **defensive**, **explicit**, and **scope-limited**.
If a behavior is not described here, it must be assumed unsafe.

---

## Trust boundaries

The following inputs are **always untrusted**:

- All HTTP request bodies, headers, query parameters, and paths
- Any trace, plan, artifact, or manifest loaded from disk
- Any corpus or evidence content supplied by the user

The HTTP boundary is defined in `src/bijux_rar/httpapi.py`.

All validation is fail-fast; malformed or suspicious input is rejected.

---

## Authentication

- Optional API key authentication via header `X-API-Token`
- Controlled by environment variable `RAR_API_TOKEN`
- If unset, the API is **explicitly unauthenticated**

There is no user model, role system, or identity management.

---

## Rate limiting

- Best-effort, per-process rate limiting
- Configured via `RAR_API_RATE_LIMIT` (requests per minute)
- No shared state, no distributed coordination

Rate limiting is a **protective measure**, not an abuse-prevention guarantee.

---

## Resource limits

All runs are bounded by explicit quotas:

- **Wall-clock time**: `RAR_RUN_TIME_BUDGET_SEC`
- **CPU time** (process clock): `RAR_RUN_CPU_BUDGET_SEC`
- **Disk usage per run**: `RAR_RUN_DISK_QUOTA_BYTES`

Quota violations terminate execution immediately.

---

## Filesystem and path safety

- All artifact paths are resolved under a single artifacts root
- Path traversal (`..`) is rejected
- Symlink escapes outside the artifacts root are rejected
- POSIX paths only

No filesystem access outside the artifacts directory is permitted.

---

## Content handling

- Request size is capped (`MAX_REQUEST_BYTES` in `httpapi.py`)
- Only JSON media types are accepted
- XML and other structured formats are explicitly rejected
- Accept headers are enforced

bijux-rar does not attempt to sanitize or interpret arbitrary user content.

---

## Artifact integrity

- All core artifacts are hashed and recorded in manifests
- Evidence references include span + content hash validation
- Provenance is enforced during verification and replay

Any hash mismatch causes verification failure.

---

## Replay and verification guarantees

Replay and verification require:

- Byte-identical traces
- Matching artifact hashes
- Stable provenance identifiers

If these conditions are not met, replay or verification fails.

There is no partial or best-effort verification mode.

---

## Explicit non-goals

The following are **out of scope by design**:

- Multi-tenant isolation beyond API key + rate limit
- TLS termination (must be handled by deployment environment)
- Secrets rotation or credential lifecycle management
- Sandboxing or execution of untrusted user code
- Defense against malicious local users

If you need these properties, you must add them externally.

---

## Vulnerability reporting

If you discover a security issue:

- **Do not** open a public GitHub issue
- Use GitHub Security Advisories
- Or contact the maintainers privately

Responsible disclosure is required.
