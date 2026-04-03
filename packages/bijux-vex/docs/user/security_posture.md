# Security Posture

Threat model

- Bijux‑Vex assumes you control the runtime environment.
- It does not protect against compromised hosts or malicious backends.

In scope

- Redaction of credentials in logs and provenance
- Explicit failure on unsafe conditions

Out of scope

- Data exfiltration prevention
- Encryption at rest for external stores

Reporting issues

- See `SECURITY.md` in the repository.
