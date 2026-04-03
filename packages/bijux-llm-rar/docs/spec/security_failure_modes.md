
STATUS: AUTHORITATIVE
## Security Failure Modes (Cheat Sheet)

- **Tamper evidence bytes**: Detected (span hash mismatch) → hard fail.
- **Delete/alter evidence files**: Detected (manifest/hash mismatch) → hard fail.
- **Use wrong corpus/index for replay**: Detected (provenance hash mismatch) → replay refused.
- **Unknown schema versions**: Detected → trace rejected.
- **Path traversal in evidence**: Detected via path validation → rejected.
- **Networked tools without recording**: Out of scope; deterministic replay requires recorded outputs.
- **Host compromise**: Out of scope; assumes trusted host.
- **Side-channel attacks**: Out of scope; not mitigated.

If any of the “out of scope” attacks succeed, the system makes no guarantees.***
