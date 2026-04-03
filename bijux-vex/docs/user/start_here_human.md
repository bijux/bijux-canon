# Start Here (Human)

You are probably here because search results changed when they shouldn’t, or because you don’t trust what your vector stack is doing in production.

Bijux‑Vex exists to make those failures visible and prevent silent drift. It gives you two clear execution paths:

- **Deterministic**: exact, replayable, and auditable.
- **ND (non‑deterministic)**: fast and scalable, but bounded and explicit.

If you only run one example, run this:

```bash
bijux vex ingest --doc "hello" --vector "[0.0, 1.0, 0.0]" --vector-store memory
bijux vex materialize --execution-contract deterministic --vector-store memory
bijux vex execute --artifact-id art-1 --execution-contract deterministic \
  --execution-intent exact_validation --execution-mode strict --vector "[0.0, 1.0, 0.0]"
```

Once that works, read:

- `docs/user/what_is_bijux_vex.md`
- `docs/user/determinism_end_to_end.md`
- `docs/user/nd_execution_model.md`
