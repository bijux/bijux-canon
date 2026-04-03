STATUS: EXPLANATORY
# Lockfile policy

- `requirements.lock` is generated via `pip freeze` from the current dev environment to make installs reproducible.
- Regenerate after dependency changes: `pip freeze > requirements.lock` in a clean venv.
- Consumers should prefer `pip install -r requirements.lock` to avoid drift when validating reproducibility or security.
