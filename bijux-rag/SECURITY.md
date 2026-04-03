# Security Policy

<a id="top"></a>

*Last updated: 2025-12-26*

Bijux projects follow **Coordinated Vulnerability Disclosure (CVD)**. Please report security issues **privately**, and allow reasonable time to investigate and ship a fix **before** public disclosure.

[Back to top](#top)

---

## Table of Contents

* [Supported Versions](#supported-versions)
* [Reporting a Vulnerability](#reporting-a-vulnerability)
* [Triage Process & Response Targets](#triage-process--response-targets)
* [Safe Harbor (Good-Faith Research)](#safe-harbor-good-faith-research)
* [Scope](#scope)
* [Secure Development Practices](#secure-development-practices)
* [Public Advisories & Credit](#public-advisories--credit)
* [Contact](#contact)

[Back to top](#top)

---

<a id="supported-versions"></a>

## Supported Versions

We patch the **latest minor line only** (mirrors Bijux org policy used across repos such as bijux-cli).

|  Version | Supported |
| -------: | :-------- |
|  `0.1.x` | Yes       |
| `<0.1.0` | No        |

When `0.2.0` is released, support for `0.1.x` ends. We do **not** backport fixes to older minor lines.

[Back to top](#top)

---

<a id="reporting-a-vulnerability"></a>

## Reporting a Vulnerability

**Do not** open a public GitHub issue for security problems.

Report privately via one of the following:

* **Preferred:** GitHub **Private Vulnerability Report**
  [https://github.com/bijux/bijux-rag/security/advisories/new](https://github.com/bijux/bijux-rag/security/advisories/new)
* **Fallback:** Email **[mousavi.bijan@gmail.com](mailto:mousavi.bijan@gmail.com)** with subject
  **`[SECURITY] Vulnerability report: bijux-rag`**

### What to include (speeds up triage)

* Affected version(s) and install method (pip/pipx/from source)
* OS, Python version, and runtime mode (CLI vs FastAPI server)
* Clear impact statement (what an attacker gains)
* Minimal reproduction steps and/or PoC
* Any mitigations/workarounds you found
* Whether you want public credit (name/handle)

Please **do not** include secrets, real user data, or production logs. If you accidentally access sensitive data, stop and report immediately.

[Back to top](#top)

---

<a id="triage-process--response-targets"></a>

## Triage Process & Response Targets

Best-effort targets (severity typically assessed using **CVSS v3.x**, plus exploitability and real-world blast radius):

* **Acknowledgement:** within **48 hours**
* **Initial assessment & provisional severity:** within **5 business days**
* **Target fix windows:**

  * **Critical:** 7 days
  * **High:** 30 days
  * **Medium:** 90 days
  * **Low:** 180 days

If a report is incomplete, the clock effectively pauses until we can reproduce or validate impact.

[Back to top](#top)

---

<a id="safe-harbor-good-faith-research"></a>

## Safe Harbor (Good-Faith Research)

We will not pursue or support legal action for good-faith research that:

* Avoids privacy violations, data exfiltration, and service disruption
* Is limited to systems, accounts, and datasets you control
* Respects rate limits and avoids volumetric DoS/stress testing
* Uses the minimum steps necessary to demonstrate impact
* Stops and reports immediately upon encountering sensitive data

If you’re unsure whether something is in scope, ask first via the private channels above.

[Back to top](#top)

---

<a id="scope"></a>

## Scope

### In scope

* This repository’s source code (`src/bijux_rag/**`)
* Published release artifacts (sdist/wheels) and the `bijux-rag` entrypoint
* Default CLI behaviors and file I/O boundaries (e.g., `process`, `index-build`, `retrieve`, `ask`)
* FastAPI surface and OpenAPI contract under `/`, including:

  * `GET  /health`
  * `POST /index/build`
  * `POST /retrieve`
  * `POST /ask`
  * `POST /chunks`
* Misconfigurations or unsafe defaults that enable:

  * RCE / arbitrary file read-write
  * authz bypass (if/when auth is added)
  * sensitive data exposure beyond intended inputs/outputs
  * dependency/supply-chain compromise attributable to our packaging/release pipeline

### Out of scope

* Social engineering or physical attacks
* Volumetric DoS / stress testing / benchmarking
* Vulnerabilities in third-party dependencies **without** a practical exploit path through bijux-rag
* Issues that require pre-existing privileged local access *and* offer no plausible escalation path
* Prompt-injection style attacks where the “impact” is only that **untrusted retrieved text influences output**
  (We treat retrieved text as untrusted by design; it becomes a security issue only if it crosses boundaries—e.g., causes unintended tool execution, file access, credential exposure, or remote code execution.)

> If the issue spans multiple Bijux repos (e.g., bijux-cli + bijux-rag), report it in either repo’s private advisory; we’ll coordinate internally.

[Back to top](#top)

---

<a id="secure-development-practices"></a>

## Secure Development Practices

bijux-rag follows the same “gated quality” philosophy used across Bijux projects:

* **Security scans (gating):** `bandit`, `pip-audit` (`make security`)
* **SBOMs:** CycloneDX generation (`make sbom`)
* **API contract hardening:** OpenAPI lint + drift checks; Schemathesis runs against endpoints (`make api`)
* **Strict typing + lint:** Ruff + MyPy + Pyright + Pytype (CI-gated)
* **Hygiene:** “zero-root-pollution” — generated outputs and caches must go under `artifacts/` (CI-gated)
* **No telemetry:** the project does not phone home; any unexpected outbound behavior is treated as a security bug

*(No public bug bounty program at this time.)*

[Back to top](#top)

---

<a id="public-advisories--credit"></a>

## Public Advisories & Credit

When a fix is available, we publish a **GitHub Security Advisory** and may request a **CVE** when appropriate. Reporter credit is included **only with your consent**.

[Back to top](#top)

---

<a id="contact"></a>

## Contact

* **Private report:** [https://github.com/bijux/bijux-rag/security/advisories/new](https://github.com/bijux/bijux-rag/security/advisories/new)
* **Email (fallback):** [mousavi.bijan@gmail.com](mailto:mousavi.bijan@gmail.com) (subject: `[SECURITY] bijux-rag`)
* **Non-security questions:** open a normal GitHub issue

Thank you for helping keep bijux-rag users safe.

[Back to top](#top)
