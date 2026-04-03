# Testing policy (frozen)

- tox runs the full test matrix across supported Python versions.
- Lint, quality, security, typing gates run once on the **oldest supported Python (3.11)** to control CI time/cost; this is intentional.
- Contributors must not “optimize” gates to run on all versions; matrix belongs in tox only.
