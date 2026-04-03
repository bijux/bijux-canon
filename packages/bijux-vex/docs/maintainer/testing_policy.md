# Testing policy (frozen)

- tox runs the full test matrix across supported Python versions.
- Lint, quality, security, typing gates run once on the **oldest supported Python (3.11)** to control CI time/cost; this is intentional.
- pytype is skipped (Python version churn + maintenance cost); do not re-enable without explicit approval. If installed, it is advisory only.
- Contributors must not “optimize” gates to run on all versions; matrix belongs in tox only.
