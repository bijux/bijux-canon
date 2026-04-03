<p align="center">
  <img src="https://raw.githubusercontent.com/bijux/bijux-vex/main/docs/assets/bijux_logo_hq.png" alt="Bijux-Vex" width="180" />
</p>

# bijux-vex

**Vector execution runtime with replayable determinism + audited ANN (nothing implicit).**

Why this exists: production vector search drifts quietly. Bijux‑Vex makes correctness explicit, and refuses when guarantees cannot be met.

If you only read one page, read this: https://bijux.github.io/bijux-vex/user/only_read_one_page/

## Why bijux-vex

- Replayable determinism for results you can defend
- Audited, bounded ND (ANN) instead of silent approximation
- Nothing implicit: fail‑closed by design

## Hello world (deterministic, exact)

```bash
bijux vex ingest --doc "hello" --vector "[0.0, 1.0, 0.0]" \
  --vector-store memory
bijux vex materialize --execution-contract deterministic --vector-store memory
bijux vex execute --artifact-id art-1 \
  --execution-contract deterministic --execution-intent exact_validation \
  --execution-mode strict --vector "[0.0, 1.0, 0.0]"
```

## Hello world (ND / ANN with quality)

```bash
bijux vex materialize --execution-contract non_deterministic --index-mode ann \
  --vector-store faiss --vector-store-uri ./index.faiss
bijux vex execute --artifact-id art-1 \
  --execution-contract non_deterministic --execution-intent exploratory_search \
  --execution-mode bounded --randomness-seed 42 --randomness-sources ann_probe \
  --nd-witness sample --vector "[0.0, 1.0, 0.0]"
```

## Concept map (instant mental model)

```
request → plan → execute → provenance
            ├─ deterministic (exact)
            └─ ND (ANN) + quality
vector store: optional + explicit
```

## When NOT to use this

- Not a vector DB (no implicit CRUD or query language)
- Not a RAG framework (no prompts, no orchestration)
- Not a hosted service (you run it)

## Stability & support

- Supported Python: 3.11–3.14
- Determinism: stable and replayable
- ND (ANN): experimental but audited and bounded

## Getting help / reporting issues

GitHub issues: https://github.com/bijux/bijux-vex/issues
Include `bijux vex debug-bundle` output when reporting a bug.

## Quick links

- Start Here (10 minutes): https://bijux.github.io/bijux-vex/user/start_here_10_minutes/
- Start Here (human): https://bijux.github.io/bijux-vex/user/start_here_human/
- Concept Map: https://bijux.github.io/bijux-vex/user/concept_map/
- ND Production Guide: https://bijux.github.io/bijux-vex/guides/nd_production/
- Security Policy: https://github.com/bijux/bijux-vex/blob/main/SECURITY.md
- Changelog: https://github.com/bijux/bijux-vex/blob/main/CHANGELOG.md
