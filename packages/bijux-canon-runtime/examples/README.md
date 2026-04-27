# Runtime Examples

These examples are the fastest way to inspect the runtime contract without
walking the whole package source tree.

## What They Cover

- `minimal_deterministic_flow.py`: a smallest-path execution that resolves one
  governed manifest and shows the canonical `execute_flow()` surface
- `non_deterministic_replay_flow.py`: a replay case where deterministic
  guarantees are intentionally violated and must be surfaced as runtime output
- `replay_policy_violation.py`: a policy-focused example that shows replay
  acceptability and verification failures as first-class results
- `boring/flow.json` and `boring/policy.json`: checked-in manifest and policy
  inputs for CLI-oriented smoke runs
- `datasets/*.jsonl`: tracked example corpora used by runtime and replay tests

## How To Use Them

Validation-first:

```bash
make -C packages/bijux-canon-runtime -f ../../makes/packages/bijux-canon-runtime.mk install
artifacts/bijux-canon-runtime/venv/bin/python packages/bijux-canon-runtime/examples/minimal_deterministic_flow.py
```

CLI-oriented replay smoke:

```bash
artifacts/bijux-canon-runtime/venv/bin/bijux-canon-runtime plan packages/bijux-canon-runtime/examples/boring/flow.json
artifacts/bijux-canon-runtime/venv/bin/bijux-canon-runtime run packages/bijux-canon-runtime/examples/boring/flow.json --policy packages/bijux-canon-runtime/examples/boring/policy.json
```

The examples are not marketing demos. They exist to prove execution shape,
replay behavior, and policy handling against tracked inputs.
