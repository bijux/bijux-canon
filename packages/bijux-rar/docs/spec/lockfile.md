STATUS: EXPLANATORY
# Lockfile policy

- `configs/bijux-rar/requirements.lock` is generated via `pip freeze` from the current dev environment to make installs reproducible.
- Regenerate after dependency changes: `pip freeze > configs/bijux-rar/requirements.lock` in a clean venv.
- Consumers should prefer `pip install -r configs/bijux-rar/requirements.lock` to avoid drift when validating reproducibility or security.
