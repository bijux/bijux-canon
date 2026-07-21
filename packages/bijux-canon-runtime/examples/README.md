# Runtime Examples

The examples exercise planning, deterministic execution, replay policy, and
non-determinism boundaries against tracked inputs.

| Path | Scenario |
| --- | --- |
| `boring/flow.json` | Strict, exact-match flow over a frozen dataset descriptor. |
| `boring/policy.json` | Deterministic baseline verification policy with halt-on-failure behavior. |
| `minimal_deterministic_flow.py` | Smallest Python execution using the canonical `execute_flow()` surface. |
| `non_deterministic_replay_flow.py` | Declared non-determinism and the replay evidence it produces. |
| `replay_policy_violation.py` | Replay acceptability and verification-policy rejection. |
| `datasets/*.jsonl` | Versioned corpora used by runtime and replay scenarios. |

## Resolve the checked-in flow

From the repository root:

```bash
RUNTIME=artifacts/bijux-canon-runtime/venv/bin/bijux-canon-runtime
FLOW=packages/bijux-canon-runtime/examples/boring/flow.json
POLICY=packages/bijux-canon-runtime/examples/boring/policy.json
STORE=artifacts/bijux-canon-runtime/examples.duckdb

"$RUNTIME" plan "$FLOW" --json
```

Plan mode produces no run identifier and does not mutate the execution store.
Inspect the resolved dataset, determinism, entropy, replay, dependency, and
verification declarations before executing.

## Execute and persist

```bash
"$RUNTIME" run "$FLOW" \
  --policy "$POLICY" \
  --db-path "$STORE" \
  --strict-determinism
```

The command creates the DuckDB store when needed and prints the run ID and
aggregate execution counts. Capture that ID together with the manifest, policy,
tenant ID, and database path; all are needed for later replay. Use
`inspect run --json` to retrieve the persisted trace. The live `--json` output
currently omits the run ID.

Do not run concurrent writers against the same store. Use a separate database
path when comparing example variants so their evidence remains easy to
attribute.

## Run the Python scenarios

```bash
artifacts/bijux-canon-runtime/venv/bin/python \
  packages/bijux-canon-runtime/examples/minimal_deterministic_flow.py

artifacts/bijux-canon-runtime/venv/bin/python \
  packages/bijux-canon-runtime/examples/non_deterministic_replay_flow.py

artifacts/bijux-canon-runtime/venv/bin/python \
  packages/bijux-canon-runtime/examples/replay_policy_violation.py
```

The non-deterministic scenarios are expected to surface reduced replay
guarantees or policy findings. Treat those outcomes as the subject of the
example, not as a clean exact-match result.

Dataset descriptors carry a storage URI and content hash. When adapting an
example, update both the referenced bytes and the declared identity; changing
only the path or only the hash creates an unreviewable dataset contract.
