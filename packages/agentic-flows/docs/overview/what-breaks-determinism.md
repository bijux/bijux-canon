# What Breaks Determinism
> Determinism failure modes and how the system treats them.

- Unseeded randomness; detected; mitigated by strict determinism checks that abort the run.
- Environment drift (dependency or OS changes); detected; mitigated by environment fingerprint mismatch failures.
- External API nondeterminism; detected when declared as entropy and budgeted, otherwise silent; mitigated only when authorized.
- Mutable datasets; detected; mitigated by dataset hash enforcement and replay mismatch failures.
- Human intervention outside declared scope; silent; not mitigated beyond audit logging.
