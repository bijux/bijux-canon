# How to Choose Execution Mode

Do you need auditability?

- Yes → deterministic exact.
- No → continue.

Do you need speed at scale?

- Yes → ND bounded.
- No → deterministic exact.

Can you tolerate approximation?

- Yes → ND bounded with witness.
- No → deterministic exact.

CLI flags

- Deterministic: `--execution-contract deterministic --execution-mode strict`
- ND bounded: `--execution-contract non_deterministic --execution-mode bounded`
