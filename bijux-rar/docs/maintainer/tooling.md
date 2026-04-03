STATUS: EXPLANATORY

# Tooling

The project uses a fixed, enforced toolchain.

All tools listed here are required.  
Changes that bypass or weaken this toolchain are not accepted.

---

## Code quality and correctness

- **Ruff**  
  Formatting and linting. Style deviations are rejected.

- **MyPy** and **Pyright**  
  Static typing and interface validation.

---

## Testing and coverage

- **Pytest** and **pytest-cov**  
  Full test execution and coverage reporting.

- **Coverage threshold**  
  Enforced for `src/bijux_rar` (default: 85%).

---

## Security and supply chain

- **pip-audit**  
  Dependency vulnerability scanning.

- **bandit**  
  Static security analysis.

- **cyclonedx-bom**  
  Software Bill of Materials (SBOM) generation.

---

## Documentation

- **MkDocs**  
  Documentation build and publication.

Documentation is treated as part of the system contract.

---

## Execution

All tooling is executed via:

```bash
make all
```
