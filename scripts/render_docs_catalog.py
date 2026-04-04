#!/usr/bin/env python3
from __future__ import annotations

import argparse
import inspect
import shutil
import textwrap
from dataclasses import dataclass
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DOCS_ROOT = ROOT / "docs"
LAST_REVIEWED = "2026-04-04"


@dataclass(frozen=True)
class PackageInfo:
    slug: str
    title: str
    description: str
    package_dir: str
    import_name: str
    cli_command: str | None
    owner: str
    owns: tuple[str, ...]
    not_owns: tuple[str, ...]
    modules: tuple[tuple[str, str], ...]
    tests: tuple[str, ...]
    interfaces: tuple[str, ...]
    artifacts: tuple[str, ...]
    examples: tuple[str, ...]
    api_specs: tuple[str, ...]
    dependencies: tuple[str, ...]
    adjacencies: tuple[str, ...]
    release_notes: tuple[str, ...]


PACKAGE_CATEGORY_PAGES = {
    "foundation": [
        ("index", "Foundation"),
        ("package-overview", "Package Overview"),
        ("scope-and-non-goals", "Scope and Non-Goals"),
        ("ownership-boundary", "Ownership Boundary"),
        ("repository-fit", "Repository Fit"),
        ("capability-map", "Capability Map"),
        ("domain-language", "Domain Language"),
        ("lifecycle-overview", "Lifecycle Overview"),
        ("dependencies-and-adjacencies", "Dependencies and Adjacencies"),
        ("change-principles", "Change Principles"),
    ],
    "architecture": [
        ("index", "Architecture"),
        ("module-map", "Module Map"),
        ("dependency-direction", "Dependency Direction"),
        ("execution-model", "Execution Model"),
        ("state-and-persistence", "State and Persistence"),
        ("integration-seams", "Integration Seams"),
        ("error-model", "Error Model"),
        ("extensibility-model", "Extensibility Model"),
        ("code-navigation", "Code Navigation"),
        ("architecture-risks", "Architecture Risks"),
    ],
    "interfaces": [
        ("index", "Interfaces"),
        ("cli-surface", "CLI Surface"),
        ("api-surface", "API Surface"),
        ("configuration-surface", "Configuration Surface"),
        ("data-contracts", "Data Contracts"),
        ("artifact-contracts", "Artifact Contracts"),
        ("entrypoints-and-examples", "Entrypoints and Examples"),
        ("operator-workflows", "Operator Workflows"),
        ("public-imports", "Public Imports"),
        ("compatibility-commitments", "Compatibility Commitments"),
    ],
    "operations": [
        ("index", "Operations"),
        ("installation-and-setup", "Installation and Setup"),
        ("local-development", "Local Development"),
        ("common-workflows", "Common Workflows"),
        ("observability-and-diagnostics", "Observability and Diagnostics"),
        ("performance-and-scaling", "Performance and Scaling"),
        ("failure-recovery", "Failure Recovery"),
        ("release-and-versioning", "Release and Versioning"),
        ("security-and-safety", "Security and Safety"),
        ("deployment-boundaries", "Deployment Boundaries"),
    ],
    "quality": [
        ("index", "Quality"),
        ("test-strategy", "Test Strategy"),
        ("invariants", "Invariants"),
        ("review-checklist", "Review Checklist"),
        ("documentation-standards", "Documentation Standards"),
        ("definition-of-done", "Definition of Done"),
        ("dependency-governance", "Dependency Governance"),
        ("change-validation", "Change Validation"),
        ("known-limitations", "Known Limitations"),
        ("risk-register", "Risk Register"),
    ],
}


PACKAGE_CATEGORY_ORDER = [
    "foundation",
    "architecture",
    "interfaces",
    "operations",
    "quality",
]


PRODUCT_PACKAGES = {
    "ingest": PackageInfo(
        slug="bijux-canon-ingest",
        title="bijux-canon-ingest",
        description=(
            "Deterministic document ingestion, chunking, retrieval assembly, and "
            "ingest-facing boundaries."
        ),
        package_dir="packages/bijux-canon-ingest",
        import_name="bijux_canon_ingest",
        cli_command="bijux-canon-ingest",
        owner="bijux-canon-ingest-docs",
        owns=(
            "document cleaning, normalization, and chunking",
            "ingest-local retrieval and indexing assembly",
            "package-local CLI and HTTP boundaries",
            "ingest-specific safeguards, adapters, and observability helpers",
        ),
        not_owns=(
            "runtime-wide replay authority and persistence",
            "cross-package vector execution semantics",
            "repository maintenance automation",
        ),
        modules=(
            ("src/bijux_canon_ingest/processing", "deterministic document transforms"),
            ("src/bijux_canon_ingest/retrieval", "retrieval-oriented models and assembly"),
            ("src/bijux_canon_ingest/application", "package workflows"),
            ("src/bijux_canon_ingest/infra", "local adapters and infrastructure helpers"),
            ("src/bijux_canon_ingest/interfaces", "CLI and HTTP boundaries"),
            ("src/bijux_canon_ingest/safeguards", "protective rules for ingest behavior"),
        ),
        tests=(
            "tests/unit for module-level behavior across processing, retrieval, and interfaces",
            "tests/e2e for package boundary coverage",
            "tests/invariants for long-lived repository promises",
            "tests/eval for corpus-backed behavior checks",
        ),
        interfaces=(
            "CLI entrypoint in src/bijux_canon_ingest/interfaces/cli/entrypoint.py",
            "HTTP boundaries under src/bijux_canon_ingest/interfaces",
            "configuration modules under src/bijux_canon_ingest/config",
        ),
        artifacts=(
            "normalized document trees",
            "chunk collections and retrieval-ready records",
            "diagnostic output produced during ingest workflows",
        ),
        examples=(
            "package README for entry framing",
            "tests/e2e fixtures for executable usage samples",
        ),
        api_specs=("apis/bijux-canon-ingest/v1/schema.yaml",),
        dependencies=("pydantic", "msgpack", "numpy", "fastapi", "uvicorn", "PyYAML"),
        adjacencies=(
            "feeds prepared material toward bijux-canon-index and bijux-canon-reason",
            "stays under runtime governance instead of defining replay authority itself",
        ),
        release_notes=("README.md", "CHANGELOG.md", "pyproject.toml"),
    ),
    "index": PackageInfo(
        slug="bijux-canon-index",
        title="bijux-canon-index",
        description=(
            "Contract-driven vector execution with replay-aware determinism, audited "
            "backend behavior, and provenance-rich result handling."
        ),
        package_dir="packages/bijux-canon-index",
        import_name="bijux_canon_index",
        cli_command=None,
        owner="bijux-canon-index-docs",
        owns=(
            "vector execution semantics and backend orchestration",
            "provenance-aware result artifacts and replay-oriented comparison",
            "plugin-backed vector store, embedding, and runner integration",
            "package-local HTTP behavior and related schemas",
        ),
        not_owns=(
            "document ingestion and normalization",
            "runtime-wide replay policy and execution governance",
            "repository maintenance automation",
        ),
        modules=(
            ("src/bijux_canon_index/domain", "execution, provenance, and request semantics"),
            ("src/bijux_canon_index/application", "workflow coordination"),
            ("src/bijux_canon_index/infra", "backends, adapters, and runtime environment helpers"),
            ("src/bijux_canon_index/interfaces", "CLI and operator-facing edges"),
            ("src/bijux_canon_index/api", "HTTP application surfaces"),
            ("src/bijux_canon_index/contracts", "stable contract definitions"),
        ),
        tests=(
            "tests/unit for API, application, contracts, domain, infra, and tooling",
            "tests/e2e for CLI workflows, API smoke, determinism gates, and provenance gates",
            "tests/conformance and tests/compat_v01 for compatibility behavior",
            "tests/stress and tests/scenarios for operational pressure checks",
        ),
        interfaces=(
            "CLI modules under src/bijux_canon_index/interfaces/cli",
            "HTTP app under src/bijux_canon_index/api",
            "OpenAPI schema files under apis/bijux-canon-index/v1",
        ),
        artifacts=(
            "vector execution result collections",
            "provenance and replay comparison reports",
            "backend-specific metadata and audit output",
        ),
        examples=(
            "tests/e2e and tests/scenarios as executable usage guides",
            "apis/bijux-canon-index/v1/openapi.v1.json for HTTP contract shape",
        ),
        api_specs=(
            "apis/bijux-canon-index/v1/schema.yaml",
            "apis/bijux-canon-index/v1/openapi.v1.json",
        ),
        dependencies=("pydantic", "typer", "fastapi"),
        adjacencies=(
            "consumes prepared inputs from ingest-oriented flows",
            "is governed by bijux-canon-runtime for final replay acceptance",
        ),
        release_notes=("README.md", "CHANGELOG.md", "pyproject.toml"),
    ),
    "reason": PackageInfo(
        slug="bijux-canon-reason",
        title="bijux-canon-reason",
        description=(
            "Deterministic evidence-aware reasoning, claim formation, verification, "
            "and traceable reasoning workflows."
        ),
        package_dir="packages/bijux-canon-reason",
        import_name="bijux_canon_reason",
        cli_command="bijux-canon-reason",
        owner="bijux-canon-reason-docs",
        owns=(
            "reasoning plans, claims, and evidence-aware reasoning models",
            "execution of reasoning steps and local tool dispatch",
            "verification and provenance checks that belong to reasoning itself",
            "package-local CLI and API boundaries",
        ),
        not_owns=(
            "runtime persistence and replay authority",
            "ingest and index engines",
            "repository tooling and release automation",
        ),
        modules=(
            ("src/bijux_canon_reason/planning", "plan construction and intermediate representation"),
            ("src/bijux_canon_reason/reasoning", "claim and reasoning semantics"),
            ("src/bijux_canon_reason/execution", "step execution and tool dispatch"),
            ("src/bijux_canon_reason/verification", "checks and validation outcomes"),
            ("src/bijux_canon_reason/traces", "trace replay and diff support"),
            ("src/bijux_canon_reason/interfaces", "CLI and serialization boundaries"),
        ),
        tests=(
            "tests/unit for planning, reasoning, execution, verification, and interfaces",
            "tests/e2e for API, CLI, replay gates, retrieval reasoning, and smoke coverage",
            "tests/perf for retrieval benchmark coverage",
            "tests/docs for documentation-linked safeguards",
        ),
        interfaces=(
            "CLI app in src/bijux_canon_reason/interfaces/cli",
            "HTTP app in src/bijux_canon_reason/api/v1",
            "schema files in apis/bijux-canon-reason/v1",
        ),
        artifacts=(
            "reasoning traces and replay diffs",
            "claim and verification outcomes",
            "evaluation suite artifacts",
        ),
        examples=(
            "tooling/evaluation_suites for controlled reasoning suites",
            "tests/e2e as executable operator examples",
        ),
        api_specs=(
            "apis/bijux-canon-reason/v1/schema.yaml",
            "apis/bijux-canon-reason/v1/pinned_openapi.json",
        ),
        dependencies=("pydantic", "typer", "fastapi"),
        adjacencies=(
            "consumes evidence prepared by ingest and retrieval provided by index",
            "relies on runtime when a run must be accepted, stored, or replayed under policy",
        ),
        release_notes=("README.md", "CHANGELOG.md", "pyproject.toml"),
    ),
    "agent": PackageInfo(
        slug="bijux-canon-agent",
        title="bijux-canon-agent",
        description=(
            "Deterministic, auditable agent orchestration with role-local behavior, "
            "pipeline control, and trace-backed results."
        ),
        package_dir="packages/bijux-canon-agent",
        import_name="bijux_canon_agent",
        cli_command="bijux-canon-agent",
        owner="bijux-canon-agent-docs",
        owns=(
            "agent role implementations and role-specific helpers",
            "deterministic orchestration of the local agent pipeline",
            "trace-backed result artifacts that explain each run",
            "package-local CLI and HTTP boundaries for agent workflows",
        ),
        not_owns=(
            "runtime-wide persistence and replay acceptance",
            "ingest and index domain ownership",
            "repository tooling and release automation",
        ),
        modules=(
            ("src/bijux_canon_agent/agents", "role-local behavior"),
            ("src/bijux_canon_agent/pipeline", "execution flow orchestration"),
            ("src/bijux_canon_agent/application", "workflow policy and graph logic"),
            ("src/bijux_canon_agent/llm", "LLM runtime integration support"),
            ("src/bijux_canon_agent/interfaces", "CLI boundaries and operator helpers"),
            ("src/bijux_canon_agent/traces", "trace-facing models and persistence helpers"),
        ),
        tests=(
            "tests/unit for local behavior and utility coverage",
            "tests/integration and tests/e2e for end-to-end workflow behavior",
            "tests/invariants for package promises that should not drift",
            "tests/api for HTTP-facing validation",
        ),
        interfaces=(
            "CLI entrypoint in src/bijux_canon_agent/interfaces/cli/entrypoint.py",
            "operator configuration under src/bijux_canon_agent/config",
            "HTTP-adjacent modules under src/bijux_canon_agent/api",
        ),
        artifacts=(
            "trace-backed final outputs",
            "workflow graph execution records",
            "operator-visible result artifacts",
        ),
        examples=(
            "tests/e2e and tests/fixtures as executable examples",
            "config/execution_policy.yaml as a concrete policy surface",
        ),
        api_specs=("apis/bijux-canon-agent/v1/schema.yaml",),
        dependencies=(
            "aiohttp",
            "typer",
            "click",
            "pydantic",
            "fastapi",
            "openai",
            "structlog",
            "pluggy",
        ),
        adjacencies=(
            "coordinates work that may call ingest, reason, and runtime components",
            "leans on runtime for governed execution and replay acceptance",
        ),
        release_notes=("README.md", "CHANGELOG.md", "pyproject.toml"),
    ),
    "runtime": PackageInfo(
        slug="bijux-canon-runtime",
        title="bijux-canon-runtime",
        description=(
            "Governed execution and replay authority with auditable "
            "non-determinism handling, persistence, and package-to-package coordination."
        ),
        package_dir="packages/bijux-canon-runtime",
        import_name="bijux_canon_runtime",
        cli_command="bijux-canon-runtime",
        owner="bijux-canon-runtime-docs",
        owns=(
            "flow execution authority",
            "replay and acceptability semantics",
            "trace capture, runtime persistence, and execution-store behavior",
            "package-local CLI and API boundaries",
        ),
        not_owns=(
            "agent composition policy",
            "ingest and index domain ownership",
            "repository tooling and release support",
        ),
        modules=(
            ("src/bijux_canon_runtime/model", "durable runtime models"),
            ("src/bijux_canon_runtime/runtime", "execution engines and lifecycle logic"),
            ("src/bijux_canon_runtime/application", "orchestration and replay coordination"),
            ("src/bijux_canon_runtime/verification", "runtime-level validation support"),
            ("src/bijux_canon_runtime/interfaces", "CLI surfaces and manifest loading"),
            ("src/bijux_canon_runtime/api", "HTTP application surfaces"),
        ),
        tests=(
            "tests/unit for api, contracts, core, interfaces, model, and runtime",
            "tests/e2e for governed flow behavior",
            "tests/regression and tests/smoke for replay and storage protection",
            "tests/golden for durable example fixtures",
        ),
        interfaces=(
            "CLI entrypoint in src/bijux_canon_runtime/interfaces/cli/entrypoint.py",
            "HTTP app in src/bijux_canon_runtime/api/v1",
            "schema files in apis/bijux-canon-runtime/v1",
        ),
        artifacts=(
            "execution store records",
            "replay decision artifacts",
            "non-determinism policy evaluations",
        ),
        examples=(
            "examples/ for minimal flows, replay violations, and datasets",
            "apis/bijux-canon-runtime/v1/schema.hash for schema integrity checks",
        ),
        api_specs=(
            "apis/bijux-canon-runtime/v1/schema.yaml",
            "apis/bijux-canon-runtime/v1/schema.hash",
        ),
        dependencies=(
            "bijux-canon-agent",
            "bijux-canon-ingest",
            "bijux-canon-reason",
            "bijux-canon-index",
            "duckdb",
            "pydantic",
        ),
        adjacencies=(
            "governs the other canonical packages instead of replacing their local ownership",
            "is the final authority for run acceptance, replay evaluation, and stored evidence",
        ),
        release_notes=("README.md", "CHANGELOG.md", "pyproject.toml"),
    ),
}


ROOT_PAGES = [
    ("index", "bijux-canon"),
    ("platform-overview", "Platform Overview"),
    ("repository-scope", "Repository Scope"),
    ("workspace-layout", "Workspace Layout"),
    ("package-map", "Package Map"),
    ("api-and-schema-governance", "API and Schema Governance"),
    ("local-development", "Local Development"),
    ("testing-and-validation", "Testing and Validation"),
    ("release-and-versioning", "Release and Versioning"),
    ("documentation-system", "Documentation System"),
]


DEV_PAGES = [
    ("index", "bijux-canon-dev"),
    ("package-overview", "Package Overview"),
    ("scope-and-non-goals", "Scope and Non-Goals"),
    ("module-map", "Module Map"),
    ("quality-gates", "Quality Gates"),
    ("security-gates", "Security Gates"),
    ("schema-governance", "Schema Governance"),
    ("release-support", "Release Support"),
    ("sbom-and-supply-chain", "SBOM and Supply Chain"),
    ("operating-guidelines", "Operating Guidelines"),
]


COMPAT_PAGES = [
    ("index", "Compatibility Packages"),
    ("compatibility-overview", "Compatibility Overview"),
    ("legacy-name-map", "Legacy Name Map"),
    ("migration-guidance", "Migration Guidance"),
    ("package-behavior", "Package Behavior"),
    ("import-surfaces", "Import Surfaces"),
    ("command-surfaces", "Command Surfaces"),
    ("release-policy", "Release Policy"),
    ("validation-strategy", "Validation Strategy"),
    ("retirement-conditions", "Retirement Conditions"),
]


TARGET_ORDER = [
    "platform",
    "ingest",
    "index",
    "reason",
    "agent",
    "runtime",
    "dev",
    "compat",
]


def clean_docs_root() -> None:
    DOCS_ROOT.mkdir(exist_ok=True)
    for child in DOCS_ROOT.iterdir():
        if child.name == "assets":
            continue
        if child.is_dir():
            shutil.rmtree(child)
            continue
        if child.suffix == ".md":
            child.unlink()


def ensure_parent(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def write_doc(path: Path, body: str) -> None:
    ensure_parent(path)
    path.write_text(body.rstrip() + "\n", encoding="utf-8")


def clean_block(text: str) -> str:
    cleaned = inspect.cleandoc(text)
    return "\n".join(
        line[12:] if line.startswith("            ") else line
        for line in cleaned.splitlines()
    )


def front_matter(title: str, owner: str, doc_type: str) -> str:
    return textwrap.dedent(
        f"""\
        ---
        title: {title}
        audience: mixed
        type: {doc_type}
        status: canonical
        owner: {owner}
        last_reviewed: {LAST_REVIEWED}
        ---
        """
    )


def bullet_lines(items: tuple[str, ...] | list[str]) -> str:
    return "\n".join(f"- {item}" for item in items)


def path_lines(items: tuple[tuple[str, str], ...]) -> str:
    return "\n".join(f"- `{path}` for {meaning}" for path, meaning in items)


def link(label: str, target: str) -> str:
    return f"[{label}]({target})"


def render_home(targets: set[str]) -> str:
    sections = ["bijux-canon"]
    for target in TARGET_ORDER:
        if target in PRODUCT_PACKAGES and target in targets:
            sections.append(PRODUCT_PACKAGES[target].title)
    if "dev" in targets:
        sections.append("bijux-canon-dev")
    if "compat" in targets:
        sections.append("compatibility packages")
    quicklinks = []
    if "platform" in targets:
        quicklinks.append('<a class="md-button md-button--primary" href="bijux-canon/">Open the repository handbook</a>')
    for target in ("ingest", "index", "reason", "agent", "runtime"):
        if target in targets:
            quicklinks.append(
                f'<a class="md-button" href="{PRODUCT_PACKAGES[target].slug}/foundation/">{PRODUCT_PACKAGES[target].title}</a>'
            )
    if "dev" in targets:
        quicklinks.append('<a class="md-button" href="bijux-canon-dev/">Open maintainer docs</a>')
    if "compat" in targets:
        quicklinks.append('<a class="md-button" href="compat-packages/">Open compatibility docs</a>')
    return "\n".join(
        [
            front_matter("bijux-canon Documentation", "bijux-canon-docs", "index"),
            "# Docs Index",
            "",
            "`bijux-canon` is the canonical documentation site for the monorepo, the five",
            "product packages, the repository maintenance package, and the legacy",
            "compatibility shims that still preserve older installation names.",
            "",
            '<div class="bijux-callout"><strong>Use this site as the current contract.</strong> ',
            "The sections beneath it are intentionally organized with one repository",
            "handbook, one maintainer handbook, one compatibility handbook, and five",
            "package handbooks that all share the same five-category spine.</div>",
            "",
            '<div class="bijux-panel-grid">',
            '  <div class="bijux-panel"><h3>Repository</h3><p>Explains the monorepo boundary, shared workflows, schemas, validation, and release intent.</p></div>',
            '  <div class="bijux-panel"><h3>Packages</h3><p>Each canonical package uses the same foundation, architecture, interfaces, operations, and quality layout.</p></div>',
            '  <div class="bijux-panel"><h3>Maintenance</h3><p>Separate sections cover the repository tooling package and the compatibility shims so their intent stays explicit.</p></div>',
            "</div>",
            "",
            '<div class="bijux-quicklinks">',
            *quicklinks,
            "</div>",
            "",
            "## Documentation Scope",
            "",
            bullet_lines(tuple(f"the {name} section" for name in sections)),
            "",
            "## Reading Map",
            "",
            "- start with [bijux-canon](bijux-canon/index.md) for repository-wide behavior",
            "- move into one product package when you need ownership details or operator guidance",
            "- use [bijux-canon-dev](bijux-canon-dev/index.md) for maintainer automation and quality gates" if "dev" in targets else "- maintainer automation pages are added when the dev section is rendered",
            "- use [compatibility packages](compat-packages/index.md) when tracing a legacy install name" if "compat" in targets else "- compatibility guidance is added when the compat section is rendered",
            "",
            "## Purpose",
            "",
            "This page routes readers into the canonical repository and package handbooks without mixing product ownership with maintenance-only or legacy-only concerns.",
            "",
            "## Stability",
            "",
            "This page is part of the canonical docs spine. Keep it aligned with the sections actually rendered in `docs/` and the packages that still ship from this repository.",
        ]
    )


def render_root_page(slug: str, title: str, targets: set[str]) -> str:
    package_links = "\n".join(
        (
            f"- [{info.title}](../{info.slug}/foundation/index.md) for {info.description.lower()}"
            if key in targets
            else f"- `{info.title}` for {info.description.lower()}"
        )
        for key, info in PRODUCT_PACKAGES.items()
    )
    root_page_links = "\n".join(
        f"- [{page_title}]({page_slug}.md)" for page_slug, page_title in ROOT_PAGES[1:]
    )
    bodies = {
        "index": textwrap.dedent(
            f"""\
            # bijux-canon

            The repository handbook explains the shared boundary around the monorepo:
            package layout, schema governance, documentation standards, validation, and
            release expectations that apply above any single package.

            <div class="bijux-callout"><strong>The monorepo is a coordination layer.</strong>
            Product behavior lives in the publishable packages under `packages/`. Shared
            repository rules live here only when they genuinely belong above package level.</div>

            ## Pages in This Section

            {root_page_links}

            ## Shared Package Map

            {package_links}

            ## Purpose

            This page explains how to use the repository handbook without duplicating the package-specific detail that belongs in the package handbooks.

            ## Stability

            This page is part of the canonical docs spine. Keep it aligned with the current repository layout and the actual package set declared in `pyproject.toml`.
            """
        ),
        "platform-overview": textwrap.dedent(
            """\
            # Platform Overview

            `bijux-canon` is a multi-package repository for deterministic ingest,
            indexing, reasoning, agent execution, runtime governance, and repository
            maintenance. Each package is publishable on its own, but the repository keeps
            their interfaces, schemas, and shared validation work in one place.

            ## What the Repository Provides

            - publishable Python distributions under `packages/`
            - shared API schemas under `apis/`
            - root automation through `Makefile`, `makes/`, and CI workflows
            - one canonical documentation system under `docs/`

            ## What the Repository Does Not Try to Be

            - a single import package with one root `src/` tree
            - a place where repository glue silently overrides package ownership
            - a documentation mirror that drifts away from the checked-in code

            ## Purpose

            This page gives the shortest description of what the repository is and why it is organized as a monorepo rather than a single distribution.

            ## Stability

            Keep this page aligned with the real package set and the root-level automation that currently exists in the repository.
            """
        ),
        "repository-scope": textwrap.dedent(
            """\
            # Repository Scope

            The root repository owns only the concerns that are shared across packages or
            that coordinate them as one releasable workspace.

            ## In Scope

            - workspace-level build and test orchestration
            - documentation, governance, and contributor-facing repository rules
            - API schema storage and drift checks that involve multiple packages
            - release tagging and versioning conventions shared across packages

            ## Out of Scope

            - package-local domain behavior that belongs inside a package handbook
            - hidden root logic that bypasses package APIs
            - undocumented exceptions to the published package boundaries

            ## Purpose

            This page keeps the repository from becoming a vague catch-all layer above the packages.

            ## Stability

            Update this page only when ownership truly moves between the repository and one of the packages.
            """
        ),
        "workspace-layout": textwrap.dedent(
            """\
            # Workspace Layout

            The repository layout is intentionally direct so maintainers can see where a
            concern belongs before they open any code.

            ## Top-Level Directories

            - `packages/` for publishable Python distributions
            - `apis/` for shared schema sources and pinned artifacts
            - `docs/` for the canonical handbook
            - `makes/` and `Makefile` for workspace automation
            - `artifacts/` for generated or checked validation outputs
            - `configs/` for root-managed tool configuration

            ## Layout Rule

            A concern should live at the root only when it serves more than one package or
            when it is about the workspace itself.

            ## Purpose

            This page provides the shortest file-system map for the repository.

            ## Stability

            Keep this page aligned with the real root directories and remove any mention of retired roots.
            """
        ),
        "package-map": textwrap.dedent(
            f"""\
            # Package Map

            The canonical packages each own a distinct slice of the overall system:

            {package_links}

            ## Shared Maintainer Packages

            - [bijux-canon-dev](../bijux-canon-dev/index.md) for repository automation, schema drift checks, SBOM support, and quality gates
            - [compatibility packages](../compat-packages/index.md) for legacy distribution and import preservation

            ## Purpose

            This page keeps the package relationships visible from one place before a reader dives into package-local detail.

            ## Stability

            Update this page only when package ownership changes, not for ordinary internal refactors.
            """
        ),
        "api-and-schema-governance": textwrap.dedent(
            """\
            # API and Schema Governance

            Shared API artifacts live under `apis/` so schema review does not depend on
            reading package source alone. This repository currently tracks schemas for
            ingest, index, reason, agent, and runtime.

            ## Governance Rules

            - package code and tracked schema files must describe the same public behavior
            - drift checks belong in `bijux-canon-dev` or package tests, not in prose alone
            - schema hashes and pinned OpenAPI artifacts should move only with reviewable intent

            ## Current Schema Roots

            - `apis/bijux-canon-agent/v1`
            - `apis/bijux-canon-index/v1`
            - `apis/bijux-canon-ingest/v1`
            - `apis/bijux-canon-reason/v1`
            - `apis/bijux-canon-runtime/v1`

            ## Purpose

            This page explains why schemas are first-class repository assets rather than incidental package outputs.

            ## Stability

            Keep this page aligned with the actual schema directories and the validation tooling that protects them.
            """
        ),
        "local-development": textwrap.dedent(
            """\
            # Local Development

            Local work should happen through the publishable packages plus the root
            orchestration commands that keep the repository consistent.

            ## Working Rules

            - make package-local changes in the owning package directory
            - use root automation when the change spans packages, schemas, or docs
            - keep documentation updates reviewable alongside the code that changes behavior

            ## Shared Inputs

            - `pyproject.toml` for commitizen and workspace metadata
            - `tox.ini` for root validation environments
            - `Makefile` and `makes/` for common workflows

            ## Purpose

            This page records the preferred development posture for the workspace without repeating package-specific setup details.

            ## Stability

            Keep this page aligned with the root automation files that actually exist.
            """
        ),
        "testing-and-validation": textwrap.dedent(
            """\
            # Testing and Validation

            Validation in `bijux-canon` is layered: packages protect their own behavior,
            while the repository protects the seams between packages, schemas, docs, and
            release conventions.

            ## Validation Layers

            - package-local unit, integration, e2e, and invariant suites
            - schema drift and packaging checks in `bijux-canon-dev`
            - repository CI workflows under `.github/workflows/`

            ## Validation Rule

            A prose promise is incomplete until either package tests or repository tooling
            can detect its drift.

            ## Purpose

            This page explains the relationship between package truth and repository truth.

            ## Stability

            Keep it aligned with the current test layout and CI workflows instead of aspirational future checks.
            """
        ),
        "release-and-versioning": textwrap.dedent(
            """\
            # Release and Versioning

            The repository uses commitizen for conventional commit messages and package
            tags for version discovery through Hatch VCS. Version resolution is therefore
            both a repository concern and a package concern.

            ## Shared Release Facts

            - root commit rules live in `pyproject.toml`
            - package versions are written to package-local `_version.py` files by Hatch VCS
            - release support helpers live in `bijux-canon-dev`

            ## Versioning Rule

            Commit messages should communicate long-lived intent clearly enough that a
            maintainer can understand them years later without opening the diff first.

            ## Purpose

            This page connects the root commit conventions to the package release mechanism.

            ## Stability

            Keep this page aligned with the release tooling that is actually configured in the repository.
            """
        ),
        "documentation-system": textwrap.dedent(
            """\
            # Documentation System

            The root documentation site is the canonical handbook for repository and
            package behavior. It is intentionally structured like the reference documentation
            in `bijux-pollenomics` and `bijux-masterclass`: one root index, section indexes,
            and topic pages with stable names and repeated layout.

            ## Documentation Rules

            - use stable filenames that describe durable intent
            - keep package handbooks on the same five-category spine
            - separate product docs, maintainer docs, and legacy-compat docs
            - update docs in the same change series that changes the underlying behavior

            ## Purpose

            This page records the handbook system itself so the structure stays intentional instead of growing ad hoc again.

            ## Stability

            Keep this page aligned with the actual docs tree and the layout rules enforced by this documentation catalog.
            """
        ),
    }
    return "\n".join(
        [
            front_matter(title, "bijux-canon-docs", "index" if slug == "index" else "guide"),
            clean_block(bodies[slug]),
        ]
    )


def render_dev_page(slug: str, title: str) -> str:
    modules = bullet_lines(
        [
            "`src/bijux_canon_dev/quality` for repository quality checks",
            "`src/bijux_canon_dev/security` for security gates",
            "`src/bijux_canon_dev/sbom` for supply-chain and bill-of-materials support",
            "`src/bijux_canon_dev/release` for release support",
            "`src/bijux_canon_dev/api` for OpenAPI and schema drift tooling",
            "`src/bijux_canon_dev/packages` for package-specific repository helpers",
        ]
    )
    dev_page_links = "\n".join(
        f"- [{page_title}]({page_slug}.md)" for page_slug, page_title in DEV_PAGES[1:]
    )
    bodies = {
        "index": textwrap.dedent(
            f"""\
            # bijux-canon-dev

            `bijux-canon-dev` is the maintainer package for repository health. It exists so
            quality gates, schema drift checks, SBOM generation, and release support have a
            clear home that is outside the end-user product surface.

            ## Pages in This Section

            {dev_page_links}

            ## Module Map

            {modules}

            ## Purpose

            This page explains how to use the maintainer handbook without confusing it with user-facing product docs.

            ## Stability

            Keep this page aligned with the actual maintainer modules that exist under `packages/bijux-canon-dev`.
            """
        ),
        "package-overview": textwrap.dedent(
            """\
            # Package Overview

            `bijux-canon-dev` is intentionally not part of the end-user runtime. It is the
            package that keeps the monorepo honest when schemas drift, security tooling
            falls behind, or release metadata becomes inconsistent.

            ## What It Owns

            - shared quality and security helpers used across packages
            - release, versioning, and SBOM helpers
            - OpenAPI and schema drift tooling
            - package-specific maintenance helpers invoked by root automation

            ## Purpose

            This page gives the shortest honest description of why the package exists.

            ## Stability

            Keep this page aligned with real maintainer behavior, not aspirational tooling that does not yet exist.
            """
        ),
        "scope-and-non-goals": textwrap.dedent(
            """\
            # Scope and Non-Goals

            `bijux-canon-dev` is for maintainers and automation.

            ## In Scope

            - CI-facing helpers
            - quality, security, SBOM, release, and schema checks
            - package-specific repository automation

            ## Out of Scope

            - user-facing runtime behavior
            - product-domain models that belong to canonical packages
            - legacy-name compatibility shims

            ## Purpose

            This page prevents maintenance code from becoming an unbounded dumping ground.

            ## Stability

            Update this page only when ownership truly moves into or out of the maintenance package.
            """
        ),
        "module-map": textwrap.dedent(
            f"""\
            # Module Map

            {modules}

            ## Purpose

            This page is the shortest code-navigation aid for `bijux-canon-dev`.

            ## Stability

            Keep it aligned with actual package modules and remove retired directories promptly.
            """
        ),
        "quality-gates": textwrap.dedent(
            """\
            # Quality Gates

            Repository quality checks live here so package code does not each reinvent the
            same maintenance logic.

            ## Current Quality Surfaces

            - dependency analysis in `quality/deptry_scan.py`
            - package-specific checks under `packages/`
            - root test coverage through `packages/bijux-canon-dev/tests`

            ## Purpose

            This page explains how the package participates in repository-wide correctness and consistency.

            ## Stability

            Keep it aligned with the actual quality checks that run in tests or CI.
            """
        ),
        "security-gates": textwrap.dedent(
            """\
            # Security Gates

            Security checks that are about repository health rather than product behavior
            live in `bijux-canon-dev`.

            ## Current Security Surfaces

            - `security/pip_audit_gate.py`
            - package tests that confirm expected security tooling behavior
            - CI integration through root workflows

            ## Purpose

            This page marks the boundary between maintenance security tooling and product runtime security behavior.

            ## Stability

            Keep it aligned with the actual checks we can execute and verify.
            """
        ),
        "schema-governance": textwrap.dedent(
            """\
            # Schema Governance

            The package owns repository-level helpers that keep API schemas and tracked
            schema artifacts synchronized with the code that claims to implement them.

            ## Current Surfaces

            - `api/openapi_drift.py`
            - tests such as `tests/test_openapi_drift.py`
            - root `apis/` directories that store reviewed schema artifacts

            ## Purpose

            This page explains why schema drift detection belongs in the maintainer package.

            ## Stability

            Keep it aligned with the actual drift tooling and tracked schema files.
            """
        ),
        "release-support": textwrap.dedent(
            """\
            # Release Support

            Shared release helpers belong here so versioning and packaging practices stay
            consistent across the repository.

            ## Current Surfaces

            - `release/version_resolver.py`
            - package metadata checks in tests
            - root commit conventions configured through commitizen

            ## Purpose

            This page records the maintenance package role in release preparation.

            ## Stability

            Keep it aligned with the real release support code and the actual versioning workflow.
            """
        ),
        "sbom-and-supply-chain": textwrap.dedent(
            """\
            # SBOM and Supply Chain

            Supply-chain visibility is a repository maintenance concern, so SBOM helpers
            live in `bijux-canon-dev` instead of being duplicated by each package.

            ## Current Surfaces

            - `sbom/requirements_writer.py`
            - `tests/test_sbom_requirements_writer.py`
            - shared dependency metadata in package `pyproject.toml` files

            ## Purpose

            This page explains the home for supply-chain oriented repository tooling.

            ## Stability

            Keep it aligned with the checked-in SBOM helpers and tests.
            """
        ),
        "operating-guidelines": textwrap.dedent(
            """\
            # Operating Guidelines

            Changes in `bijux-canon-dev` should be especially careful because they can
            affect multiple packages at once.

            ## Guidelines

            - prefer checks that are reviewable and testable over opaque shell glue
            - keep repository automation explicit about which packages it touches
            - document maintainer-only behavior in this section rather than in user-facing package pages

            ## Purpose

            This page records the expected maintenance posture for the package.

            ## Stability

            Update these guidelines only when the repository operating model genuinely changes.
            """
        ),
    }
    return "\n".join(
        [
            front_matter(title, "bijux-canon-dev-docs", "index" if slug == "index" else "guide"),
            clean_block(bodies[slug]),
        ]
    )


def render_compat_page(slug: str, title: str) -> str:
    mappings = [
        ("agentic-flows", "bijux-canon-runtime"),
        ("bijux-agent", "bijux-canon-agent"),
        ("bijux-rag", "bijux-canon-ingest"),
        ("bijux-rar", "bijux-canon-reason"),
        ("bijux-vex", "bijux-canon-index"),
    ]
    mapping_lines = "\n".join(f"- `{legacy}` maps to `{canonical}`" for legacy, canonical in mappings)
    compat_page_links = "\n".join(
        f"- [{page_title}]({page_slug}.md)" for page_slug, page_title in COMPAT_PAGES[1:]
    )
    bodies = {
        "index": textwrap.dedent(
            f"""\
            # Compatibility Packages

            The compatibility packages preserve older distribution names, import names,
            and command names while the canonical package family now lives under the
            `bijux-canon-*` naming system.

            ## Pages in This Section

            {compat_page_links}

            ## Legacy Name Map

            {mapping_lines}

            ## Purpose

            This page explains the role of the compatibility handbooks without encouraging new work to start there.

            ## Stability

            Keep it aligned with the legacy packages that still ship from `packages/compat-*`.
            """
        ),
        "compatibility-overview": textwrap.dedent(
            """\
            # Compatibility Overview

            These packages exist to reduce migration breakage, not to become the preferred
            long-term entrypoints for new work.

            ## Preserved Surfaces

            - legacy distribution names
            - legacy Python import names
            - legacy command names where they still exist

            ## Purpose

            This page gives the shortest honest description of why the compatibility packages remain.

            ## Stability

            Keep it aligned with the actual compatibility promises that are still checked in.
            """
        ),
        "legacy-name-map": textwrap.dedent(
            f"""\
            # Legacy Name Map

            {mapping_lines}

            ## Purpose

            This page provides the exact mapping between retired public names and current canonical names.

            ## Stability

            Update it only when a compatibility package is added or retired.
            """
        ),
        "migration-guidance": textwrap.dedent(
            """\
            # Migration Guidance

            New work should target the canonical package names directly and treat the
            compatibility packages as temporary bridges.

            ## Recommended Migration Pattern

            - switch dependencies to the canonical `bijux-canon-*` distribution
            - switch imports to the canonical package docs and source roots
            - keep compatibility packages only where an external environment still depends on them

            ## Purpose

            This page tells maintainers how to move away from legacy names without ambiguity.

            ## Stability

            Keep it aligned with the canonical packages that compatibility packages currently point to.
            """
        ),
        "package-behavior": textwrap.dedent(
            """\
            # Package Behavior

            Each compatibility package is intentionally thin: package metadata, minimal
            import surface preservation, build glue, and documentation pointing at the
            canonical replacement.

            ## Expected Behavior

            - preserve name-based compatibility
            - avoid becoming an independent product surface
            - defer real behavior to the canonical package

            ## Purpose

            This page describes the intended minimalism of the compatibility layer.

            ## Stability

            Keep it aligned with the actual package contents in `packages/compat-*`.
            """
        ),
        "import-surfaces": textwrap.dedent(
            """\
            # Import Surfaces

            Compatibility imports exist only so older code can keep resolving package names
            during migration.

            ## Current Import Roots

            - `agentic_flows`
            - `bijux_agent`
            - `bijux_rag`
            - `bijux_rar`
            - `bijux_vex`

            ## Purpose

            This page explains which Python import names remain preserved.

            ## Stability

            Keep it aligned with the `src/` roots inside the compatibility packages.
            """
        ),
        "command-surfaces": textwrap.dedent(
            """\
            # Command Surfaces

            Some compatibility packages also preserve historic command names so migration
            does not break operator scripts immediately.

            ## Command Rule

            A compatibility command should only exist when the canonical package still
            provides a meaningful route behind it.

            ## Purpose

            This page records the intent behind legacy command preservation.

            ## Stability

            Keep it aligned with the command declarations in compatibility package metadata.
            """
        ),
        "release-policy": textwrap.dedent(
            """\
            # Release Policy

            Compatibility packages should release only when they still serve a real
            migration need or when the canonical target package changes in a way that
            requires compatibility metadata to move with it.

            ## Policy

            - keep releases narrow and clearly justified
            - avoid feature growth inside the compatibility packages
            - document canonical targets in every compatibility package README

            ## Purpose

            This page keeps compatibility releases from drifting into independent product work.

            ## Stability

            Keep it aligned with the current maintenance strategy for legacy packages.
            """
        ),
        "validation-strategy": textwrap.dedent(
            """\
            # Validation Strategy

            Compatibility packages are small, but they still need validation for import
            preservation, packaging metadata, and migration pointers.

            ## Validation Focus

            - import resolution
            - packaging metadata correctness
            - links and references to the canonical package docs

            ## Purpose

            This page explains what counts as sufficient validation for the compatibility layer.

            ## Stability

            Keep it aligned with the actual compatibility package tests or maintenance checks.
            """
        ),
        "retirement-conditions": textwrap.dedent(
            """\
            # Retirement Conditions

            A compatibility package can be retired only when the dependent environments
            that still need it are understood and the retirement path is documented.

            ## Retirement Signals

            - no remaining supported consumers depend on the legacy name
            - migration guidance has been in place long enough to be credible
            - removal will not silently strand existing automation

            ## Purpose

            This page explains the threshold for removing a compatibility package.

            ## Stability

            Update this page only when the retirement policy itself changes.
            """
        ),
    }
    return "\n".join(
        [
            front_matter(title, "bijux-canon-compat-docs", "index" if slug == "index" else "guide"),
            clean_block(bodies[slug]),
        ]
    )


def package_section_summary(category: str, package: PackageInfo) -> str:
    summaries = {
        "foundation": f"{package.title} exists to own {package.description.lower()}",
        "architecture": f"{package.title} architecture pages describe how modules and responsibilities fit together under `{package.import_name}`.",
        "interfaces": f"{package.title} interface pages describe the command, API, configuration, import, and artifact surfaces that a caller can rely on.",
        "operations": f"{package.title} operations pages describe how to install, run, observe, release, and safely operate the package.",
        "quality": f"{package.title} quality pages describe the tests, invariants, limits, and review rules that keep the package trustworthy over time.",
    }
    return summaries[category]


def related_links(package: PackageInfo, category: str) -> str:
    root = ".."
    section_links = []
    for other in PACKAGE_CATEGORY_ORDER:
        if other == category:
            continue
        section_links.append(f"- [{other.title()}]({root}/{other}/index.md)")
    return "\n".join(section_links)


def render_package_page(package: PackageInfo, category: str, slug: str, title: str) -> str:
    section_root = f"../../{package.slug}/{category}"
    package_root = f"../../{package.slug}"
    category_page_links = "\n".join(
        f"- [{page_title}]({page_slug}.md)"
        for page_slug, page_title in PACKAGE_CATEGORY_PAGES[category][1:]
    )
    if slug == "index":
        body = textwrap.dedent(
            f"""\
            # {title}

            {package_section_summary(category, package)}

            ## Pages in This Section

            {category_page_links}

            ## Read Across the Package

            {related_links(package, category)}

            ## Purpose

            This page explains how to use the {category} section for `{package.title}` without repeating the detail that belongs on the topic pages beneath it.

            ## Stability

            This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.
            """
        )
    else:
        body = render_package_topic(package, category, slug, title, package_root)
    return "\n".join(
        [
            front_matter(title, package.owner, "index" if slug == "index" else "guide"),
            clean_block(body),
        ]
    )


def render_package_topic(
    package: PackageInfo,
    category: str,
    slug: str,
    title: str,
    package_root: str,
) -> str:
    shared = {
        "foundation": {
            "package-overview": f"""# {title}

`{package.title}` is the package that owns {package.description.lower()}

## What It Owns

{bullet_lines(package.owns)}

## What It Does Not Own

{bullet_lines(package.not_owns)}

## Purpose

This page gives the shortest honest description of what the package is for.

## Stability

Keep it aligned with the real package boundary described by the code and tests.
""",
            "scope-and-non-goals": f"""# {title}

The package boundary exists so neighboring packages can evolve without hidden overlap.

## In Scope

{bullet_lines(package.owns)}

## Out of Scope

{bullet_lines(package.not_owns)}

## Purpose

This page keeps future work from leaking into the wrong package.

## Stability

Update it only when ownership truly moves into or out of `{package.title}`.
""",
            "ownership-boundary": f"""# {title}

Ownership in `{package.title}` is easiest to read from the source tree plus the tests that protect it.

## Owned Code Areas

{path_lines(package.modules)}

## Adjacent Systems

{bullet_lines(package.adjacencies)}

## Purpose

This page ties package ownership to concrete directories instead of abstract slogans.

## Stability

Keep it aligned with the current module layout.
""",
            "repository-fit": f"""# {title}

`{package.title}` sits inside the monorepo as one publishable package with its own `src/`,
tests, metadata, and release history.

## Repository Relationships

{bullet_lines(package.adjacencies)}

## Canonical Package Root

- `{package.package_dir}`
- `{package.package_dir}/src/{package.import_name}`
- `{package.package_dir}/tests`

## Purpose

This page explains how the package fits into the repository without restating repository-wide rules.

## Stability

Keep it aligned with the package's checked-in directories and actual neighboring packages.
""",
            "capability-map": f"""# {title}

The package capabilities can be read as a map from modules to behavior.

## Capability Map

{path_lines(package.modules)}

## Produced Artifacts

{bullet_lines(package.artifacts)}

## Purpose

This page helps a reader quickly map package claims to code areas.

## Stability

Keep it aligned with the real package modules and generated outputs.
""",
            "domain-language": f"""# {title}

The package should use language that reflects its actual ownership instead of borrowing
vague names from neighboring packages.

## Package Vocabulary Anchors

- package name: `{package.title}`
- Python import root: `{package.import_name}`
- owning package directory: `{package.package_dir}`
- key outputs: {", ".join(package.artifacts)}

## Purpose

This page records the naming anchors that should stay stable in docs, code, and review discussions.

## Stability

Keep it aligned with the package's real import names, directories, and artifact nouns.
""",
            "lifecycle-overview": f"""# {title}

Every package run follows a simple lifecycle: inputs enter through interfaces, domain and
application code coordinate the work, and durable artifacts or responses leave the package.

## Lifecycle Anchors

- entry surfaces: {", ".join(package.interfaces)}
- code ownership: {", ".join(path for path, _ in package.modules[:3])}
- durable outputs: {", ".join(package.artifacts)}

## Purpose

This page keeps the package lifecycle readable before a reader dives into implementation detail.

## Stability

Keep it aligned with the current entrypoints and produced outputs.
""",
            "dependencies-and-adjacencies": f"""# {title}

Package dependencies matter because they reveal which behavior is local and which behavior is delegated.

## Direct Dependency Themes

{bullet_lines(package.dependencies)}

## Adjacent Package Relationships

{bullet_lines(package.adjacencies)}

## Purpose

This page explains which surrounding tools and packages `{package.title}` depends on to do its job.

## Stability

Keep it aligned with `pyproject.toml` and the actual package seams.
""",
            "change-principles": f"""# {title}

Changes in `{package.title}` should keep the package boundary easier to understand, not harder.

## Principles

- prefer moving behavior toward the owning package instead of letting boundary overlap grow
- update docs and tests in the same change series that changes package behavior
- keep names stable and descriptive enough to survive years of maintenance

## Purpose

This page records the package-specific contribution posture.

## Stability

Update these principles only when the package operating model truly changes.
""",
        },
        "architecture": {
            "module-map": f"""# {title}

The architecture of `{package.title}` is easiest to understand from the major module groups.

## Major Modules

{path_lines(package.modules)}

## Purpose

This page provides a shortest-path code map for the package.

## Stability

Keep it aligned with the actual source directories under `{package.package_dir}`.
""",
            "dependency-direction": f"""# {title}

The package should keep dependency direction readable: domain intent near the center,
interfaces and infrastructure at the edges.

## Directional Reading Order

- domain and model concerns under the core module groups
- application orchestration that composes domain behavior
- interfaces, APIs, and adapters that sit at the boundary

## Concrete Anchors

{path_lines(package.modules)}

## Purpose

This page makes dependency direction explicit enough to review during refactors.

## Stability

Keep it aligned with current imports and directory responsibilities.
""",
            "execution-model": f"""# {title}

`{package.title}` executes work by receiving inputs at its interfaces, coordinating policy
and workflows in application code, and delegating specific responsibilities to owned modules.

## Execution Anchors

- entry surfaces: {", ".join(package.interfaces)}
- workflow modules: {", ".join(path for path, _ in package.modules[:3])}
- outputs: {", ".join(package.artifacts)}

## Purpose

This page summarizes the package execution model before readers inspect individual modules.

## Stability

Keep it aligned with the actual workflow code and entrypoints.
""",
            "state-and-persistence": f"""# {title}

State in `{package.title}` should be explicit enough that a maintainer can say what is
transient, what is serialized, and what neighboring packages must not assume.

## Durable Surfaces

{bullet_lines(package.artifacts)}

## Code Areas to Inspect

{path_lines(package.modules)}

## Purpose

This page marks the package's state and artifact boundary.

## Stability

Keep it aligned with the actual artifact shapes and serialized outputs.
""",
            "integration-seams": f"""# {title}

Integration seams are the points where `{package.title}` meets configuration, APIs,
operators, or neighboring packages.

## Integration Surfaces

{bullet_lines(package.interfaces)}

## Adjacent Systems

{bullet_lines(package.adjacencies)}

## Purpose

This page explains where to look when integration behavior changes.

## Stability

Keep it aligned with real boundary modules and schema files.
""",
            "error-model": f"""# {title}

The package error model should make it clear which failures are local validation issues,
which are dependency failures, and which are contract violations.

## Review Anchors

- inspect interface modules for operator-facing error shape
- inspect application and domain modules for orchestration failures
- inspect tests for the failure cases the package already protects

## Test Areas

{bullet_lines(package.tests)}

## Purpose

This page records how to reason about failures in architecture review.

## Stability

Keep it aligned with the actual error-handling behavior and tests.
""",
            "extensibility-model": f"""# {title}

Extension work should use the package seams that already exist instead of bypassing ownership.

## Likely Extension Areas

{path_lines(package.modules)}

## Extension Rule

Add extension points where the package already expects variation, and document them next to the owning boundary.

## Purpose

This page helps maintainers extend the package without smearing responsibilities together.

## Stability

Keep it aligned with the package seams that actually support extension today.
""",
            "code-navigation": f"""# {title}

When you need to understand a change in `{package.title}`, use this reading order:

## Reading Order

- start at the relevant interface or API module
- move into the owning application or domain module
- finish in the tests that protect the behavior

## Concrete Anchors

{path_lines(package.modules)}

## Test Anchors

{bullet_lines(package.tests)}

## Purpose

This page shortens the path from an issue report to the relevant code.

## Stability

Keep it aligned with the real source tree and current test layout.
""",
            "architecture-risks": f"""# {title}

Architectural risk appears when the package boundary becomes hard to explain or hard to test.

## Risk Signals

- behavior moves into the wrong package because it seems convenient
- interfaces start depending on lower-level implementation details directly
- produced artifacts stop matching their documented contract

## Review Areas

{path_lines(package.modules)}

## Purpose

This page keeps architectural review focused on durable package risks instead of transient churn.

## Stability

Keep it aligned with the package structure and known review concerns.
""",
        },
        "interfaces": {
            "cli-surface": f"""# {title}

The CLI surface is the operator-facing command layer for `{package.title}`.

## Command Facts

- canonical command: `{package.cli_command or "no package-level console script is declared"}`
- interface modules: {", ".join(package.interfaces)}

## Purpose

This page points maintainers toward the command entrypoints and their owning code.

## Stability

Keep it aligned with the declared scripts and the interface modules that implement them.
""",
            "api-surface": f"""# {title}

HTTP-facing behavior should be discoverable from tracked schema files and the owning API modules.

## API Artifacts

{bullet_lines(package.api_specs)}

## Boundary Modules

{bullet_lines(package.interfaces)}

## Purpose

This page ties API behavior to tracked code and schema assets.

## Stability

Keep it aligned with the actual API modules and schema files.
""",
            "configuration-surface": f"""# {title}

Configuration belongs at the package boundary, not scattered through unrelated modules.

## Configuration Anchors

{bullet_lines(package.interfaces)}

## Review Rule

Configuration changes should update the operator docs, schema docs, and tests that protect the same behavior.

## Purpose

This page explains where configuration enters the package and how it should be reviewed.

## Stability

Keep it aligned with real configuration loaders, defaults, and operator-facing options.
""",
            "data-contracts": f"""# {title}

Data contracts in `{package.title}` include schemas, structured models, and any stable
payload shape that neighboring systems are expected to understand.

## Contract Anchors

{bullet_lines(package.api_specs)}

## Artifact Anchors

{bullet_lines(package.artifacts)}

## Purpose

This page explains which structured shapes deserve compatibility review.

## Stability

Keep it aligned with tracked schemas, stable models, and durable artifacts.
""",
            "artifact-contracts": f"""# {title}

Produced artifacts are part of the package contract whenever another package, operator,
or replay workflow depends on them.

## Current Artifacts

{bullet_lines(package.artifacts)}

## Purpose

This page marks which outputs need stable review when behavior changes.

## Stability

Keep it aligned with the package outputs that are actually produced and consumed.
""",
            "entrypoints-and-examples": f"""# {title}

The fastest way to understand the package interfaces is to pair entrypoints with concrete examples.

## Entrypoints

{bullet_lines(package.interfaces)}

## Example Anchors

{bullet_lines(package.examples)}

## Purpose

This page records where maintainers can find real invocation examples instead of inventing them from scratch.

## Stability

Keep it aligned with the checked-in examples, fixtures, and executable tests.
""",
            "operator-workflows": f"""# {title}

Operator workflows should start from documented package entrypoints and end in reviewable outputs.

## Workflow Anchors

- entry surfaces: {", ".join(package.interfaces)}
- durable outputs: {", ".join(package.artifacts)}
- validation backstops: {", ".join(package.tests[:2])}

## Purpose

This page connects package interfaces to the workflows an operator actually performs.

## Stability

Keep it aligned with the existing commands, endpoints, and outputs.
""",
            "public-imports": f"""# {title}

The public Python surface of `{package.title}` starts at the package import root and any
intentionally exported modules beneath it.

## Import Anchor

- import root: `{package.import_name}`
- package source root: `{package.package_dir}/src/{package.import_name}`

## Purpose

This page keeps the import-facing contract visible when refactoring package internals.

## Stability

Keep it aligned with the actual package source tree and documented import paths.
""",
            "compatibility-commitments": f"""# {title}

Compatibility in `{package.title}` should be explicit: stable commands, tracked schemas,
durable artifacts, and release notes that explain intentional breakage.

## Compatibility Anchors

{bullet_lines(package.release_notes)}

## Review Rule

Breaking changes must be visible in code, docs, and validation together.

## Purpose

This page describes what should trigger compatibility review for the package.

## Stability

Keep it aligned with the package's actual public surfaces and release process.
""",
        },
        "operations": {
            "installation-and-setup": f"""# {title}

Installation for `{package.title}` should start from the package metadata and the specific
optional dependencies that matter for the work being done.

## Package Metadata Anchors

- package root: `{package.package_dir}`
- metadata file: `{package.package_dir}/pyproject.toml`
- readme: `{package.package_dir}/README.md`

## Dependency Themes

{bullet_lines(package.dependencies)}

## Purpose

This page tells maintainers where setup truth actually lives for the package.

## Stability

Keep it aligned with `pyproject.toml` and the checked-in package metadata.
""",
            "local-development": f"""# {title}

Local development should happen inside `{package.package_dir}` with tests and docs updated
in the same change series as the code.

## Development Anchors

{bullet_lines(package.tests)}

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
""",
            "common-workflows": f"""# {title}

Most work on `{package.title}` follows one of a few recurring paths.

## Recurring Paths

- inspect the package README and section indexes first
- follow an interface into the owning module group
- run the owning tests before declaring the change complete

## Code Areas

{path_lines(package.modules)}

## Purpose

This page makes common package workflows easier to repeat consistently.

## Stability

Keep it aligned with the actual package structure and tests.
""",
            "observability-and-diagnostics": f"""# {title}

Diagnostics should make it easier to explain what `{package.title}` did, not merely that it ran.

## Diagnostic Anchors

{bullet_lines(package.artifacts)}

## Supporting Modules

{path_lines(tuple(item for item in package.modules if "observability" in item[0] or "trace" in item[0] or "result" in item[0]) or package.modules[:2])}

## Purpose

This page points readers toward the package's observable output and diagnostic support.

## Stability

Keep it aligned with the package modules and artifacts that currently support diagnosis.
""",
            "performance-and-scaling": f"""# {title}

Performance work should preserve the deterministic and contract-driven behavior the package already promises.

## Performance Review Anchors

- inspect workflow modules before optimizing boundary code blindly
- use the package tests that exercise realistic workloads
- treat artifact and contract drift as a regression even when performance improves

## Test Anchors

{bullet_lines(package.tests)}

## Purpose

This page records the posture for performance work in `{package.title}`.

## Stability

Keep it aligned with the package's actual performance-sensitive paths and validation surfaces.
""",
            "failure-recovery": f"""# {title}

Failure recovery starts with knowing which artifacts, interfaces, and tests expose the problem.

## Recovery Anchors

- interface surfaces: {", ".join(package.interfaces)}
- artifacts to inspect: {", ".join(package.artifacts)}
- tests to run: {", ".join(package.tests[:2])}

## Purpose

This page gives maintainers a durable frame for triaging package failures.

## Stability

Keep it aligned with the package entrypoints and diagnostic outputs.
""",
            "release-and-versioning": f"""# {title}

Release work for `{package.title}` depends on package metadata, tracked release notes, and
the repository's commit conventions.

## Release Anchors

{bullet_lines(package.release_notes)}

## Versioning Anchors

- version file: `{package.package_dir}/src/{package.import_name}/_version.py`
- tag pattern is configured in `{package.package_dir}/pyproject.toml`

## Purpose

This page ties package-local release mechanics to the wider repository release model.

## Stability

Keep it aligned with the package metadata and current versioning configuration.
""",
            "security-and-safety": f"""# {title}

Security review in `{package.title}` should focus on the package's real boundary surfaces and outputs.

## Review Anchors

{bullet_lines(package.interfaces)}

## Safety Rule

Any change that broadens package authority should update docs, tests, and release notes together.

## Purpose

This page keeps security review grounded in concrete package seams.

## Stability

Keep it aligned with the package interfaces and operational risk profile.
""",
            "deployment-boundaries": f"""# {title}

Deployment for `{package.title}` should respect the package boundary instead of assuming the full repository is always present.

## Boundary Facts

- package root: `{package.package_dir}`
- public metadata: `{package.package_dir}/pyproject.toml`
- release notes: `{package.package_dir}/CHANGELOG.md` when present

## Purpose

This page reminds maintainers that packages are publishable units, not just folders in one repo.

## Stability

Keep it aligned with the package's actual distributable surface.
""",
        },
        "quality": {
            "test-strategy": f"""# {title}

The tests for `{package.title}` are the executable proof of its package contract.

## Test Areas

{bullet_lines(package.tests)}

## Purpose

This page explains the broad testing shape of the package.

## Stability

Keep it aligned with the real test directories and the behaviors they protect.
""",
            "invariants": f"""# {title}

Invariants are the promises that should survive ordinary implementation change.

## Invariant Anchors

- package boundary stays explicit
- interface and artifact contracts remain reviewable
- tests continue to prove the long-lived promises

## Supporting Tests

{bullet_lines(package.tests)}

## Purpose

This page records the kinds of promises that should not drift casually.

## Stability

Keep it aligned with invariant-focused tests and documented package guarantees.
""",
            "review-checklist": f"""# {title}

Reviewing changes in `{package.title}` should include both behavior and documentation.

## Checklist

- did ownership stay inside the correct package boundary
- do interface or artifact changes have matching docs and tests
- are filenames, commit messages, and symbols still clear enough to age well

## Purpose

This page records a compact review lens for package changes.

## Stability

Update it only when the package review posture genuinely changes.
""",
            "documentation-standards": f"""# {title}

Package docs should stay consistent with the shared handbook layout used across the repository.

## Standards

- use the shared five-category package spine
- prefer stable filenames that describe durable intent
- keep docs grounded in real code paths, interfaces, and artifacts

## Purpose

This page keeps package docs from drifting back into ad hoc structure.

## Stability

Update it only when the shared documentation system itself changes.
""",
            "definition-of-done": f"""# {title}

A change in `{package.title}` is not done when code passes locally but the package contract
is still unclear or unprotected.

## Done Means

- code, docs, and tests agree on the new behavior
- public surfaces and artifacts remain explainable
- release-facing impact is visible when compatibility changes

## Purpose

This page records the package's completion threshold.

## Stability

Keep it aligned with the package validation and release expectations.
""",
            "dependency-governance": f"""# {title}

Dependency changes in `{package.title}` should be treated as contract changes when they
alter package authority, operational risk, or public setup expectations.

## Current Dependency Themes

{bullet_lines(package.dependencies)}

## Purpose

This page explains why dependency review matters for the package.

## Stability

Keep it aligned with `pyproject.toml` and the package's real dependency posture.
""",
            "change-validation": f"""# {title}

Validation after a change should target the package surfaces that were actually touched.

## Validation Targets

- interface changes should update interface docs and owning tests
- artifact changes should update artifact docs and consuming tests
- architectural changes should update section pages that explain the package seam

## Test Anchors

{bullet_lines(package.tests)}

## Purpose

This page records how to choose meaningful validation for package work.

## Stability

Keep it aligned with the package's current test layout and docs structure.
""",
            "known-limitations": f"""# {title}

No package is improved by pretending its limitations do not exist.

## Honest Boundaries

{bullet_lines(package.not_owns)}

## Purpose

This page keeps limitation language attached to the package boundary instead of scattered through issue comments.

## Stability

Keep it aligned with the limitations that remain intentionally true today.
""",
            "risk-register": f"""# {title}

The durable risks for `{package.title}` are the ones that make the package boundary, interface contract,
or produced artifacts harder to trust.

## Ongoing Risks to Watch

- hidden overlap with neighboring packages
- drift between docs, code, and tests
- compatibility changes that are not made explicit

## Purpose

This page keeps long-lived package risks visible to maintainers.

## Stability

Update it when the durable risk profile changes, not for routine day-to-day churn.
""",
        },
    }
    return shared[category][slug]


def write_platform_docs(targets: set[str]) -> None:
    write_doc(DOCS_ROOT / "index.md", render_home(targets))
    base = DOCS_ROOT / "bijux-canon"
    for slug, title in ROOT_PAGES:
        write_doc(base / f"{slug}.md", render_root_page(slug, title, targets))


def write_package_docs(package_key: str) -> None:
    package = PRODUCT_PACKAGES[package_key]
    base = DOCS_ROOT / package.slug
    for category in PACKAGE_CATEGORY_ORDER:
        for slug, title in PACKAGE_CATEGORY_PAGES[category]:
            write_doc(base / category / f"{slug}.md", render_package_page(package, category, slug, title))


def write_dev_docs() -> None:
    base = DOCS_ROOT / "bijux-canon-dev"
    for slug, title in DEV_PAGES:
        write_doc(base / f"{slug}.md", render_dev_page(slug, title))


def write_compat_docs() -> None:
    base = DOCS_ROOT / "compat-packages"
    for slug, title in COMPAT_PAGES:
        write_doc(base / f"{slug}.md", render_compat_page(slug, title))


def nav_lines(targets: set[str]) -> list[str]:
    lines = [
        "nav:",
        "  - Home: index.md",
    ]
    if "platform" in targets:
        lines.extend(
            [
                "  - bijux-canon:",
                *[
                    f"      - {title}: bijux-canon/{slug}.md"
                    for slug, title in ROOT_PAGES
                ],
            ]
        )
    for key in ("ingest", "index", "reason", "agent", "runtime"):
        if key not in targets:
            continue
        package = PRODUCT_PACKAGES[key]
        lines.append(f"  - {package.title}:")
        for category in PACKAGE_CATEGORY_ORDER:
            lines.append(f"      - {category.title()}:")
            for slug, title in PACKAGE_CATEGORY_PAGES[category]:
                lines.append(
                    f"          - {title}: {package.slug}/{category}/{slug}.md"
                )
    if "dev" in targets:
        lines.extend(
            [
                "  - bijux-canon-dev:",
                *[
                    f"      - {title}: bijux-canon-dev/{slug}.md"
                    for slug, title in DEV_PAGES
                ],
            ]
        )
    if "compat" in targets:
        lines.extend(
            [
                "  - Compatibility Packages:",
                *[
                    f"      - {title}: compat-packages/{slug}.md"
                    for slug, title in COMPAT_PAGES
                ],
            ]
        )
    return lines


def write_mkdocs(targets: set[str]) -> None:
    body = "\n".join(
        [
            "site_name: bijux-canon",
            "site_url: https://github.com/bijux/bijux-canon",
            "repo_name: bijux/bijux-canon",
            "repo_url: https://github.com/bijux/bijux-canon",
            "",
            "docs_dir: docs",
            "",
            "theme:",
            "  name: material",
            "  language: en",
            "  logo: assets/bijux_logo_hq.png",
            "  favicon: assets/bijux_icon.png",
            "  features:",
            "    - navigation.instant",
            "    - navigation.tabs",
            "    - navigation.sections",
            "    - navigation.indexes",
            "    - navigation.footer",
            "    - content.code.copy",
            "",
            "extra_css:",
            "  - assets/styles/extra.css",
            "",
            *nav_lines(targets),
            "",
            "plugins:",
            "  - search",
            "",
            "markdown_extensions:",
            "  - admonition",
            "  - attr_list",
            "  - md_in_html",
            "  - tables",
            "  - toc:",
            "      permalink: true",
        ]
    )
    (ROOT / "mkdocs.yml").write_text(body + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render the canonical bijux-canon documentation catalog."
    )
    parser.add_argument(
        "targets",
        nargs="*",
        choices=TARGET_ORDER,
        help="Sections to render. Defaults to all sections.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    targets = set(args.targets or TARGET_ORDER)
    clean_docs_root()
    if "platform" in targets:
        write_platform_docs(targets)
    for key in ("ingest", "index", "reason", "agent", "runtime"):
        if key in targets:
            write_package_docs(key)
    if "dev" in targets:
        write_dev_docs()
    if "compat" in targets:
        write_compat_docs()
    if not (DOCS_ROOT / "index.md").exists():
        write_doc(DOCS_ROOT / "index.md", render_home(targets))
    else:
        write_doc(DOCS_ROOT / "index.md", render_home(targets))
    write_mkdocs(targets)
    count = len(list(DOCS_ROOT.rglob("*.md")))
    print(f"Rendered {count} Markdown files for targets: {', '.join(sorted(targets))}")


if __name__ == "__main__":
    main()
