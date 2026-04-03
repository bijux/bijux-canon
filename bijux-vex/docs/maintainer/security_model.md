# Security & abuse model

In scope:

- Replay poisoning: mitigated via provenance hashes and immutable artifacts.
- Artifact spoofing: mitigated via fingerprint checks and audit chain.
- Capability refusal: ND without ANN results in `NDExecutionUnavailableError`.
- Authz denial: mutations blocked via `Authz` contracts.

Out of scope:

- Multi-tenant isolation guarantees.
- Network-level ACLs beyond Authz hooks.
- Side-channel attacks or timing analysis.

Operator guidance:

- Treat provenance ledger as tamper-evident; rotate or archive per retention policy.
- Run divergence detection to catch backend drift.
- Do not bypass invariants via retry wrappers.
- Vulnerability posture: `py==1.11.0` triggers PYSEC-2022-42969 with no upstream fix yet. SBOM generation ignores this ID explicitly until a patched release is available; upgrade once released.
