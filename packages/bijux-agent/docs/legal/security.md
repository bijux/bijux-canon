# Security

## Reporting a vulnerability

If you believe you have found a security issue:

- Do not open a public GitHub issue with sensitive details.
- Prefer GitHub Security Advisories (if enabled for the repository) or contact the maintainers privately.

Include:

- a clear description of the issue,
- reproduction steps,
- affected versions/commits (if known),
- impact assessment (data exposure, RCE, etc.).

## Data handling notes

- The CLI reads local files and may write derived artifacts under the chosen `--out` run directory.
- The HTTP API handler snapshots request text to disk under `./artifacts/api/inputs/` to preserve auditability.
- Treat `artifacts/` as sensitive if inputs are sensitive.

## Secrets and API keys

- API keys are read from environment variables (optionally via a `.env` file).
- Do not commit `.env` or other secret material to version control.
- Rotate keys immediately if you suspect exposure.

## Third-party providers

When configured, the system may send document content to external model providers. You are responsible for ensuring that this is acceptable for your data and threat model.
