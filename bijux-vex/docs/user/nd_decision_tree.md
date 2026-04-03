# ND Decision Tree

Do you need speed more than exact replay?

- If no: use deterministic exact.
- If yes: continue.

Is recall critical for user-facing decisions?

- If yes: set `nd.target_recall` and enable witness `sample` or `full`.
- If no: use `fast` or `balanced` profile.

Is latency budget strict?

- If yes: set `nd.latency_budget_ms` and accept possible refusal.
- If no: use `accurate` profile and larger candidate caps.

Need auditability?

- Enable witness mode and keep provenance artifacts.

Recommended starting configs

- Fast: `profile=fast`, `witness=off`, `budget=low`.
- Balanced: `profile=balanced`, `witness=sample`.
- Accurate: `profile=accurate`, `witness=full`.
