# ND Troubleshooting

## Why this exists

When ND fails, it often fails in ways that look like “bad search.” This guide helps you diagnose and fix the real cause quickly.

If you skip this, you can waste time tuning the wrong knobs or blaming your data.

## Story / scenario

An ops team sees rising latency and unstable results after a deployment. The issue is an index drift and an overly strict budget.

## What usually goes wrong

- Index drift after ingest changes.
- Budgets set without realistic expectations.
- Backend outages mistaken for quality issues.

## How Bijux-Vex handles it

ND exposes explicit refusal reasons and quality metrics so you can pinpoint the issue.

## What trade-offs remain

- Some fixes require rebuilds or higher budgets.
- Some instability is unavoidable at scale.

## Where to go deeper

- `docs/user/nd_quality_confidence.md`
- `docs/user/nd_parameters.md`

---

Low recall

- Increase `nd.target_recall` or use `accurate` profile.
- Enable witness mode to validate quality.

High latency

- Reduce candidate limits or use `fast` profile.
- Lower `top_k` if possible.

Unstable results

- Provide an explicit seed.
- Ensure index hash and parameters are stable across runs.

Backend unavailable

- Check `bijux vex vdb status`.
- Verify backend installation and credentials.

Index drift

- Rebuild the ND index.
- Ensure corpus fingerprint matches the artifact.
