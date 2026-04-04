# Contracts

The stable contract surface of `bijux-canon-agent` is larger than just the
console command. It includes every surface that operators, tests, and adjacent
packages are expected to rely on.

## Stable surfaces

- the `bijux-canon-agent` console entrypoint
- the package-local HTTP surface under `api/v1/`
- trace and result artifact shapes exposed through `traces/` and core models
- configuration and environment inputs that callers are expected to set intentionally

## Change policy

- change public behavior only when the new behavior is deliberate and documented
- update docs and tests in the same review as the contract change
- keep internal refactors internal by preserving boundary behavior and artifact meaning

## Practical test

If a downstream caller, operator, or recorded trace would notice the change,
treat it as a contract change even if the Python refactor looks local.
