# ND Quality & Confidence

## Why this exists

ND quality metrics tell you whether the results are stable enough to use. Without them, you might ship low-quality results that look fine in development but fail in production.

This section is for anyone who needs to make **operational decisions** about ND quality—engineers, analysts, and on-call responders.

## Story / scenario

A recommendation model drifts after a data update. Metrics reveal a spike in instability, and the team rolls back before users notice.

## What usually goes wrong

- Teams treat ANN results as “good enough” without measuring.
- Confidence labels are not used to gate downstream behavior.

## How Bijux-Vex handles it

ND results include quality metrics and a confidence label so downstream systems can act safely.

## What trade-offs remain

- Measuring quality costs time.
- Witness checks can be expensive at scale.

## Where to go deeper

- `docs/user/nd_examples.md`
- `docs/user/nd_decision_tree.md`

---

Quality metrics

- Rank instability: how sensitive the ordering is.
- Distance margin: how separated the top-k neighbors are.
- Similarity entropy: how uniform the scores are.

Witness modes

- `off`: no witness check, metrics reported as not measured.
- `sample`: exact verification on a small subset.
- `full`: exact verification on full candidates.

Confidence labels

- `high_confidence`: stable ranking and clear margins.
- `medium_confidence`: acceptable variance.
- `low_confidence`: unstable or low-signal results.

What to do with low confidence

- Reduce `k` or increase recall targets.
- Enable witness mode.
- Switch to deterministic exact for verification.

Example ND report (simplified)

```json
{
  "quality": {
    "rank_instability": 0.12,
    "distance_margin": 0.45,
    "similarity_entropy": 0.62
  },
  "confidence": "medium_confidence",
  "witness": "sample"
}
```

## Common misunderstandings

- “Confidence is subjective.” It is derived from explicit metrics.
- “Low confidence means failure.” It means you should verify or adjust.
- “Metrics are optional.” They are required for ND safety.
