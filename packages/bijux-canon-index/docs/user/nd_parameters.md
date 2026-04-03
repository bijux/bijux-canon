# Choosing ND Parameters Without Being an ANN Expert

## Why this exists

ANN parameters are easy to get wrong. This section gives you safe, human-scale choices so you can move fast without becoming an ANN specialist.

If you skip this, you may ship results that are too slow, too unstable, or too low-quality for your use case.

## Story / scenario

A team turns on ANN with default parameters. Latency improves, but recall drops and nobody notices until users complain. A profile or target recall would have caught this.

## What usually goes wrong

- Teams copy parameters from unrelated benchmarks.
- Budgets are set without understanding the trade-offs.

## How Bijux-Vex handles it

Use explicit profiles and budgets to control ND behavior safely.

## What trade-offs remain

- Better quality usually costs more latency.
- Lower budgets may trigger refusals.

## Where to go deeper

- `docs/user/nd_decision_tree.md`
- `docs/user/nd_quality_confidence.md`

---

Profiles

- `fast`: minimize latency, lower recall.
- `balanced`: default tradeoff.
- `accurate`: higher recall with more work.

Latency budget

- Use `nd.latency_budget_ms` to bound query time.
- ND refuses if it cannot meet the budget with the chosen profile.

Target recall

- Use `nd.target_recall` when you care about quality.
- If the backend cannot honor the target, ND refuses or degrades with explicit reporting.

When to tune

- Use `bijux vex nd tune` on a representative dataset.
- Apply the recommended config in your `bijux_vex.toml`.

When to refuse

- If you cannot declare a seed or randomness sources.
- If budget and target recall are incompatible.
