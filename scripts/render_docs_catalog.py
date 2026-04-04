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


def mermaid_block(source: str) -> str:
    return "\n".join(["```mermaid", source.rstrip(), "```"])


def insert_after_intro(body: str, block: str) -> str:
    lines = body.splitlines()
    split_index = len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            split_index = index
            break
    head = "\n".join(lines[:split_index]).rstrip()
    tail = "\n".join(lines[split_index:]).lstrip()
    return "\n\n".join(part for part in (head, block.strip(), tail) if part)


def insert_before_heading(body: str, heading: str, block: str) -> str:
    marker = f"## {heading}"
    if marker not in body:
        return "\n\n".join([body.rstrip(), block.strip()])
    return body.replace(marker, block.strip() + "\n\n" + marker, 1)


def render_route_diagram(
    scope_title: str,
    section_title: str,
    page_title: str,
    destination_titles: tuple[str, ...],
) -> str:
    destination_nodes = []
    destination_edges = []
    for index, title in enumerate(destination_titles, start=1):
        node_name = f"dest{index}"
        destination_nodes.append(f'    {node_name}["{title}"]')
        destination_edges.append(f"    page --> {node_name}")
    return mermaid_block(
        "\n".join(
            [
                "flowchart LR",
                f'    scope["{scope_title}"] --> section["{section_title}"]',
                f'    section --> page["{page_title}"]',
                *destination_nodes,
                *destination_edges,
            ]
        )
    )


def render_focus_diagram(
    page_title: str,
    focus_sections: tuple[tuple[str, tuple[str, ...]], ...],
) -> str:
    lines = ["flowchart TD", f'    page["{page_title}"]']
    for index, (section_title, detail_titles) in enumerate(focus_sections, start=1):
        section_node = f"focus{index}"
        lines.append(f'    {section_node}["{section_title}"]')
        lines.append(f"    page --> {section_node}")
        for detail_index, detail_title in enumerate(detail_titles, start=1):
            detail_node = f"{section_node}_{detail_index}"
            lines.append(f'    {detail_node}["{detail_title}"]')
            lines.append(f"    {section_node} --> {detail_node}")
    return mermaid_block("\n".join(lines))


def add_page_route_map(
    body: str,
    scope_title: str,
    section_title: str,
    page_title: str,
    destination_titles: tuple[str, ...],
    focus_sections: tuple[tuple[str, tuple[str, ...]], ...],
) -> str:
    block = "\n".join(
        [
            "## Page Maps",
            "",
            render_route_diagram(scope_title, section_title, page_title, destination_titles),
            "",
            render_focus_diagram(page_title, focus_sections),
        ]
    )
    return insert_after_intro(body, block)


def add_question_section(body: str, questions: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## What This Page Answers",
            "",
            bullet_lines(questions),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def package_page_questions(
    package: PackageInfo,
    category: str,
    title: str,
) -> tuple[str, ...]:
    question_map = {
        "foundation": (
            f"what {package.title} is expected to own",
            "what remains outside the package boundary",
            "which neighboring seams a reviewer should compare next",
        ),
        "architecture": (
            f"how {package.title} is structured internally",
            "which modules control the main execution path",
            "where architectural drift would become visible first",
        ),
        "interfaces": (
            f"which public or operator-facing surfaces {package.title} exposes",
            "which artifacts and schemas act like contracts",
            "what compatibility pressure this surface creates",
        ),
        "operations": (
            f"how {package.title} is installed, run, diagnosed, and released",
            "which files or tests matter during package operation",
            "where an operator should look when behavior changes",
        ),
        "quality": (
            f"what proves the {package.title} contract today",
            "which risks or limits still need explicit review",
            "what a reviewer should verify before accepting change",
        ),
    }
    return question_map[category]


def package_page_reader_fit(
    package: PackageInfo,
    category: str,
) -> tuple[str, ...]:
    fit_map = {
        "foundation": (
            "you need the package boundary before reading implementation detail",
            "you are deciding whether work belongs in this package or a neighboring one",
            "you need the shortest stable description of package intent",
        ),
        "architecture": (
            "you are tracing internal structure or execution flow",
            "you need to understand where modules fit before refactoring",
            "you are reviewing architectural drift instead of one local bug",
        ),
        "interfaces": (
            "you need the public command, API, import, or artifact surface",
            "you are checking whether a caller can rely on a given shape or entrypoint",
            "you need the contract-facing side of the package before using it",
        ),
        "operations": (
            "you are installing, running, diagnosing, or releasing the package",
            "you need operational anchors rather than conceptual framing",
            "you are responding to package behavior in a local or CI environment",
        ),
        "quality": (
            "you are reviewing tests, invariants, limitations, or risk",
            "you need evidence that the documented contract is actually protected",
            "you are deciding whether a change is done rather than merely implemented",
        ),
    }
    return fit_map[category]


def package_page_reviewer_lens(
    package: PackageInfo,
    category: str,
) -> tuple[str, ...]:
    lens_map = {
        "foundation": (
            "compare the stated package boundary with the owned modules and tests",
            "check that out-of-scope work is not quietly reintroduced through adjacent packages",
            "confirm that the package description still matches the real repository layout",
        ),
        "architecture": (
            "trace the claimed execution path through the listed modules",
            "look for dependency direction that now contradicts the documented seam",
            "verify that architectural risks still match the current code structure",
        ),
        "interfaces": (
            "compare commands, API files, imports, and artifacts against the documented surface",
            "check whether schema or artifact changes need compatibility review",
            "confirm that operator-facing examples still point at real entrypoints",
        ),
        "operations": (
            "verify that setup, workflow, and release references still match package metadata",
            "check that operational docs point at current diagnostics and validation paths",
            "confirm that release-facing claims match the package's actual versioning files",
        ),
        "quality": (
            "compare the documented proof strategy with the current test layout",
            "look for limitations or risks that should have been updated by recent changes",
            "verify that the page's definition of done still reflects real validation practice",
        ),
    }
    return lens_map[category]


def package_honesty_boundary(package: PackageInfo, category: str) -> str:
    honesty_map = {
        "foundation": (
            f"This page can explain the intended boundary of {package.title}, but it does not"
            " replace the code and tests that ultimately prove that boundary."
        ),
        "architecture": (
            f"This page describes the current structural model of {package.title}, but it does"
            " not by itself prove that every import or runtime path still obeys that model."
        ),
        "interfaces": (
            f"This page can identify the intended public surfaces of {package.title}, but real"
            " compatibility still depends on code, schemas, artifacts, and tests staying aligned."
        ),
        "operations": (
            f"This page explains how {package.title} is expected to be operated, but it does"
            " not replace package metadata, runtime behavior, or validation runs in a real environment."
        ),
        "quality": (
            f"This page explains how {package.title} protects itself, but it does not claim"
            " that prose alone is enough without the listed tests, checks, and review practice."
        ),
    }
    return honesty_map[category]


def package_anchor_bullets(package: PackageInfo, category: str) -> tuple[str, ...]:
    anchor_map = {
        "foundation": (
            f"`{package.package_dir}` as the package root",
            f"`{package.package_dir}/src/{package.import_name}` as the import boundary",
            f"`{package.package_dir}/tests` as the package proof surface",
        ),
        "architecture": tuple(
            f"`{path}` for {meaning}" for path, meaning in package.modules[:3]
        ),
        "interfaces": (
            *(f"{item}" for item in package.interfaces[:3]),
            package.api_specs[0] if package.api_specs else package.release_notes[0],
        ),
        "operations": (
            f"`{package.package_dir}/pyproject.toml` for package metadata",
            f"`{package.package_dir}/README.md` for local package framing",
            f"`{package.package_dir}/tests` for executable operational backstops",
        ),
        "quality": (
            package.tests[0],
            package.tests[1] if len(package.tests) > 1 else package.tests[0],
            package.release_notes[0],
        ),
    }
    return tuple(anchor_map[category])


def package_core_claim(package: PackageInfo, category: str) -> str:
    claim_map = {
        "foundation": (
            f"The foundational claim of `{package.title}` is that its package boundary can be"
            " explained in stable ownership terms instead of by implementation accident."
        ),
        "architecture": (
            f"The architectural claim of `{package.title}` is that its structure is deliberate"
            " enough for a reviewer to trace responsibilities, dependencies, and drift pressure"
            " without reverse-engineering the entire codebase."
        ),
        "interfaces": (
            f"The interface claim of `{package.title}` is that commands, APIs, imports, schemas,"
            " and artifacts form a reviewable contract rather than an implied one."
        ),
        "operations": (
            f"The operational claim of `{package.title}` is that install, run, diagnose, and"
            " release paths can be repeated from explicit package assets instead of oral history."
        ),
        "quality": (
            f"The quality claim of `{package.title}` is that tests, invariants, risks, and"
            " completion criteria jointly prove whether the package is trustworthy after change."
        ),
    }
    return claim_map[category]


def package_why_it_matters(package: PackageInfo, category: str) -> str:
    matter_map = {
        "foundation": (
            f"If the foundation pages for `{package.title}` are weak, reviewers stop knowing"
            " where the package boundary really is and adjacent packages begin absorbing"
            " behavior by convenience instead of design."
        ),
        "architecture": (
            f"If the architecture pages for `{package.title}` are weak, refactors become"
            " guesswork and dependency drift can hide until failures show up in tests or"
            " production-facing behavior."
        ),
        "interfaces": (
            f"If the interface pages for `{package.title}` are weak, callers cannot tell"
            " which commands, schemas, or artifacts are stable enough to depend on, and"
            " compatibility review arrives too late."
        ),
        "operations": (
            f"If the operations pages for `{package.title}` are weak, maintainers end up"
            " relearning install, diagnose, and release behavior from trial and error"
            " instead of from checked-in package truth."
        ),
        "quality": (
            f"If the quality pages for `{package.title}` are weak, it becomes difficult to"
            " tell whether a change is actually safe or merely passes a narrow local test."
        ),
    }
    return matter_map[category]


def package_if_it_drifts(package: PackageInfo, category: str) -> tuple[str, ...]:
    drift_map = {
        "foundation": (
            "ownership starts migrating by convenience instead of by explicit package boundary",
            "neighboring packages inherit responsibilities without deliberate review",
            "reviewers lose confidence that the package description still means anything stable",
        ),
        "architecture": (
            "dependency direction becomes harder to inspect quickly",
            "refactors can land without anyone noticing structural regressions until later",
            "code navigation becomes slower because the documented map no longer matches reality",
        ),
        "interfaces": (
            "callers depend on surfaces that are less stable than the docs imply",
            "schema and artifact changes stop receiving the compatibility review they need",
            "operator examples begin pointing at stale or misleading entrypaths",
        ),
        "operations": (
            "maintainers relearn package operation by trial and error",
            "release and setup steps quietly diverge from the checked-in package metadata",
            "diagnostic workflows become harder to repeat under incident pressure",
        ),
        "quality": (
            "reviewers cannot tell whether the listed proof still covers the real risk surface",
            "limitations stop being visible until they show up as rework later",
            "definition-of-done language drifts away from actual validation practice",
        ),
    }
    return drift_map[category]


def package_scenario(package: PackageInfo, category: str) -> str:
    scenario_map = {
        "foundation": (
            f"A contributor proposes moving new behavior into `{package.title}` because it is"
            " nearby in the repository. This page should make it obvious whether that work"
            " fits the package boundary or belongs in a neighboring package instead."
        ),
        "architecture": (
            f"A reviewer is tracing a refactor through `{package.title}` and needs to know"
            " whether the changed modules still line up with the documented execution and"
            " dependency structure."
        ),
        "interfaces": (
            f"An operator or downstream caller wants to depend on a `{package.title}` surface"
            " and needs to know which command, API, schema, import, or artifact is stable"
            " enough to treat as a contract."
        ),
        "operations": (
            f"A maintainer is trying to run, diagnose, or release `{package.title}` under time"
            " pressure and needs an explicit path that starts from checked-in metadata and"
            " lands in repeatable validation."
        ),
        "quality": (
            f"A change appears correct locally, but the reviewer still needs to know whether"
            f" `{package.title}` has actually satisfied its proof obligations before the work"
            " is accepted."
        ),
    }
    return scenario_map[category]


def package_source_of_truth(package: PackageInfo, category: str) -> tuple[str, ...]:
    truth_map = {
        "foundation": (
            f"`{package.package_dir}/src/{package.import_name}` for the real ownership boundary in code",
            f"`{package.package_dir}/tests` for executable proof of that boundary",
            f"`{package.package_dir}/README.md` and this section for the shortest maintained framing",
        ),
        "architecture": (
            f"`{package.package_dir}/src/{package.import_name}` for the actual dependency and module structure",
            f"`{package.package_dir}/tests` for structural and behavioral regressions",
            "this page for the reviewer-facing map that should remain aligned with those assets",
        ),
        "interfaces": (
            f"`{package.package_dir}/src/{package.import_name}` for the implemented boundary",
            *(f"`{item}` as tracked contract evidence" for item in package.api_specs[:1]),
            f"`{package.package_dir}/tests` for compatibility and behavior proof",
        ),
        "operations": (
            f"`{package.package_dir}/pyproject.toml` for install and release metadata",
            f"`{package.package_dir}/README.md` and package tests for operator truth",
            "this page for the repeatable workflow narrative that should match those assets",
        ),
        "quality": (
            f"`{package.package_dir}/tests` for executable proof",
            f"`{package.package_dir}/pyproject.toml` for declared package constraints",
            "this page for the review lens that explains how to read that proof",
        ),
    }
    return tuple(truth_map[category])


def package_common_misreadings(package: PackageInfo, category: str) -> tuple[str, ...]:
    misreading_map = {
        "foundation": (
            f"that `{package.title}` owns any nearby behavior just because it is convenient",
            "that a boundary statement is enough without the code and tests that enforce it",
            "that out-of-scope means unimportant rather than owned elsewhere",
        ),
        "architecture": (
            "that the documented module map guarantees every import is still clean automatically",
            "that one current implementation path is the whole architecture contract",
            "that diagrams replace the need to inspect the concrete modules listed here",
        ),
        "interfaces": (
            "that every visible package surface is equally stable",
            "that one schema or example is the whole compatibility story",
            "that interface docs override package code, artifacts, or tests when they disagree",
        ),
        "operations": (
            "that the shortest operator path is the same thing as the most authoritative source",
            "that setup or release behavior can be inferred without checking package metadata",
            "that passing one local run proves the operational contract is fully intact",
        ),
        "quality": (
            "that a passing local test automatically satisfies the package review standard",
            "that documented risks are static and do not need to move with the code",
            "that the definition of done is only about implementation rather than proof",
        ),
    }
    return misreading_map[category]


def package_next_checks(package: PackageInfo, category: str) -> tuple[str, ...]:
    next_map = {
        "foundation": (
            "move to architecture when the question becomes structural rather than boundary-oriented",
            "move to interfaces when the question becomes contract-facing",
            "move to quality when the question becomes proof or review sufficiency",
        ),
        "architecture": (
            "move to interfaces when the review reaches a public or operator-facing seam",
            "move to operations when the concern becomes repeatable runtime behavior",
            "move to quality when you need proof that the documented structure is still protected",
        ),
        "interfaces": (
            "move to operations when the caller-facing question becomes procedural or environmental",
            "move to quality when compatibility or evidence of protection becomes the real issue",
            "move back to architecture when a public-surface question reveals a deeper structural drift",
        ),
        "operations": (
            "move to interfaces when the operational path depends on a specific surface contract",
            "move to quality when the question becomes whether the workflow is sufficiently proven",
            "move back to architecture when operational complexity suggests a structural problem",
        ),
        "quality": (
            "move to foundation when the risk appears to be boundary confusion rather than missing tests",
            "move to architecture when the proof gap points to structural drift",
            "move to interfaces or operations when the proof question is really about a contract or workflow",
        ),
    }
    return next_map[category]


def package_update_triggers(package: PackageInfo, category: str) -> tuple[str, ...]:
    trigger_map = {
        "foundation": (
            "package ownership moves between this package and a neighboring one",
            "the package description, core outputs, or boundary modules materially change",
            "tests or docs reveal that the old boundary explanation is no longer accurate",
        ),
        "architecture": (
            "module responsibilities or dependency direction change materially",
            "new execution pathways or structural seams become important to review",
            "architectural risk shifts enough that the current map is misleading",
        ),
        "interfaces": (
            "commands, schemas, API modules, imports, or artifacts change in a caller-visible way",
            "compatibility expectations change or a new contract surface appears",
            "examples or entrypoints stop matching the actual package boundary",
        ),
        "operations": (
            "install, setup, diagnostics, or release behavior changes materially",
            "package metadata or runtime workflow changes the expected operator path",
            "new operational constraints appear that a maintainer needs to know before acting",
        ),
        "quality": (
            "test layout, invariant protection, or risk posture changes materially",
            "definition-of-done or validation practice changes in a way reviewers must understand",
            "known limitations or evidence expectations move with the codebase",
        ),
    }
    return trigger_map[category]


def package_working_interpretation(package: PackageInfo, category: str) -> str:
    interpretation_map = {
        "foundation": (
            f"Read the {category} pages for `{package.title}` as the package's durable"
            " self-description: they should explain the package in terms that remain"
            " intelligible even after ordinary refactors."
        ),
        "architecture": (
            f"Read the {category} pages for `{package.title}` as a reviewer-facing map"
            " of structure and flow: they should be detailed enough to shorten code"
            " reading without pretending to replace it."
        ),
        "interfaces": (
            f"Read the {category} pages for `{package.title}` as the bridge between"
            " implementation and caller expectations: they should make public surfaces"
            " legible before a downstream dependency is formed."
        ),
        "operations": (
            f"Read the {category} pages for `{package.title}` as the package's explicit"
            " operating memory: they should make common tasks repeatable for a maintainer"
            " who does not want to recover the workflow from scratch."
        ),
        "quality": (
            f"Read the {category} pages for `{package.title}` as the proof frame around"
            " the package: they should explain how trust is earned, defended, and revised"
            " after change."
        ),
    }
    return interpretation_map[category]


def package_decision_rule(package: PackageInfo, category: str, title: str) -> str:
    rule_map = {
        "foundation": (
            f"Use `{title}` to decide whether a change clarifies or blurs `{package.title}` as a bounded package. "
            "If the work expands package authority without a cleaner ownership story, the default answer should be to stop and re-check the boundary before implementation continues."
        ),
        "architecture": (
            f"Use `{title}` to decide whether a structural change makes `{package.title}` easier or harder to explain in terms of modules, dependency direction, and execution flow. "
            "If the change only works because the architecture becomes less legible, the page should push the reviewer toward redesign rather than acceptance."
        ),
        "interfaces": (
            f"Use `{title}` to decide whether a caller-facing surface is explicit enough to be depended on. "
            "If the surface cannot be tied back to concrete code, schemas, artifacts, and tests, it should be treated as unstable until that evidence exists."
        ),
        "operations": (
            f"Use `{title}` to decide whether a maintainer can repeat the package workflow from checked-in assets instead of memory. "
            "If a step only works when tribal knowledge fills the gap, the page should drive the reviewer back toward clearer operational documentation or simpler behavior."
        ),
        "quality": (
            f"Use `{title}` to decide whether `{package.title}` has actually earned trust after a change. "
            "If the package passes one narrow check but leaves the wider contract, risk, or validation story unclear, the correct answer is that the work is not done yet."
        ),
    }
    return rule_map[category]


def package_what_good_looks_like(package: PackageInfo, category: str, title: str) -> tuple[str, ...]:
    good_map = {
        "foundation": (
            f"`{title}` leaves a reviewer able to explain `{package.title}` in one boundary sentence without hand-waving",
            "the owned and out-of-scope areas read as complementary rather than contradictory",
            "neighboring packages become easier to place because this package is clearly bounded",
        ),
        "architecture": (
            f"`{title}` lets a reviewer trace structure without guessing where the real pathway lives",
            "the documented module relationships make refactors easier to reason about before code is changed",
            "the page shortens code reading by pointing at the right structural hotspots first",
        ),
        "interfaces": (
            f"`{title}` leaves a caller knowing which surfaces are explicit enough to trust",
            "the contract discussion ties together commands, schemas, artifacts, and tests instead of treating them separately",
            "compatibility review becomes a visible step rather than an afterthought",
        ),
        "operations": (
            f"`{title}` leaves a maintainer able to repeat the relevant package workflow from checked-in assets",
            "the operational path is explicit enough that incident pressure does not force guesswork",
            "release and setup expectations stay aligned with the package metadata and tests",
        ),
        "quality": (
            f"`{title}` leaves a reviewer able to say why the package should be trusted after a change",
            "tests, limitations, and risk language reinforce one another instead of competing",
            "the completion bar is demanding enough to prevent shallow acceptance",
        ),
    }
    return good_map[category]


def add_reader_fit_section(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Use This Page When",
            "",
            bullet_lines(bullets),
        ]
    )
    if "## What This Page Answers" in body:
        return insert_before_heading(body, "What This Page Answers", block)
    return insert_before_heading(body, "Purpose", block)


def add_reviewer_lens_section(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Reviewer Lens",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_honesty_boundary(body: str, text: str) -> str:
    block = "\n".join(
        [
            "## Honesty Boundary",
            "",
            text,
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_section_contract(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Section Contract",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_reading_advice(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Reading Advice",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_anchor_section(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Concrete Anchors",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Use This Page When", block)


def add_core_claim(body: str, text: str) -> str:
    block = "\n".join(
        [
            "## Core Claim",
            "",
            text,
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_why_it_matters(body: str, text: str) -> str:
    block = "\n".join(
        [
            "## Why It Matters",
            "",
            text,
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_if_it_drifts(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## If It Drifts",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_representative_scenario(body: str, text: str) -> str:
    block = "\n".join(
        [
            "## Representative Scenario",
            "",
            text,
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_source_of_truth(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Source Of Truth Order",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_common_misreadings(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Common Misreadings",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Concrete Anchors", block)


def add_next_checks(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Next Checks",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_update_triggers(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Update This Page When",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Purpose", block)


def add_working_interpretation(body: str, text: str) -> str:
    lines = body.splitlines()
    split_index = len(lines)
    for index, line in enumerate(lines[1:], start=1):
        if line.startswith("## "):
            split_index = index
            break
    head = "\n".join(lines[:split_index]).rstrip()
    tail = "\n".join(lines[split_index:]).lstrip()
    return "\n\n".join(part for part in (head, text.strip(), tail) if part)


def add_decision_rule(body: str, text: str) -> str:
    block = "\n".join(
        [
            "## Decision Rule",
            "",
            text,
        ]
    )
    if "## What This Page Answers" in body:
        return insert_before_heading(body, "What This Page Answers", block)
    return insert_before_heading(body, "Purpose", block)


def add_what_good_looks_like(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## What Good Looks Like",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Core Claim", block)


def render_home(
    targets: set[str],
    categories_by_package: dict[str, tuple[str, ...]],
) -> str:
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
        if target in targets and "foundation" in categories_by_package.get(target, ()):
            quicklinks.append(
                f'<a class="md-button" href="{PRODUCT_PACKAGES[target].slug}/foundation/">{PRODUCT_PACKAGES[target].title}</a>'
            )
    if "dev" in targets:
        quicklinks.append('<a class="md-button" href="bijux-canon-dev/">Open maintainer docs</a>')
    if "compat" in targets:
        quicklinks.append('<a class="md-button" href="compat-packages/">Open compatibility docs</a>')
    body = "\n".join(
        [
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
    body = add_page_route_map(
        body,
        "bijux-canon",
        "Root Site",
        "Docs Index",
        tuple(f"{name} section" for name in sections),
        (
            ("Repository", ("shared rules", "workspace scope")),
            ("Packages", ("five product handbooks", "stable package spine")),
            ("Maintenance", ("dev handbook", "compatibility handbook")),
        ),
    )
    body = add_working_interpretation(
        body,
        "Treat the root page as the routing layer for the whole documentation system. Its job is not to duplicate every handbook, but to make the correct next reading choice obvious before the reader commits to a longer path.",
    )
    body = add_reader_fit_section(
        body,
        (
            "you are orienting yourself before opening a repository, package, maintainer, or compatibility page",
            "you need the fastest route to the correct handbook section",
            "you are reviewing whether the current docs system covers the right surfaces",
        ),
    )
    body = add_decision_rule(
        body,
        "Use this page to decide where a question belongs in the documentation system before you spend time reading deeply. If the page cannot route the reader to a single clearly better next section, then the root documentation structure itself needs revision.",
    )
    body = add_what_good_looks_like(
        body,
        (
            "the correct next handbook path becomes obvious within a few seconds",
            "the root page reduces orientation cost instead of adding another layer of ambiguity",
            "the documentation system feels intentionally divided rather than accidentally scattered",
        ),
    )
    body = add_question_section(
        body,
        (
            "which handbook to open first for a given repository question",
            "how the repository, package, maintainer, and compatibility docs relate",
            "what the current documentation system is expected to cover",
        ),
    )
    body = add_reviewer_lens_section(
        body,
        (
            "check that every rendered handbook section still belongs in the root site",
            "look for package or maintainer material that should have moved to a more specific section",
            "confirm that the home page still routes readers to the fastest useful entrypoint",
        ),
    )
    body = add_honesty_boundary(
        body,
        "This page can route readers to the right section quickly, but it does not replace the more specific handbook pages that prove package, maintainer, or compatibility details.",
    )
    body = add_section_contract(
        body,
        (
            "route readers into the correct repository, package, maintainer, or compatibility section",
            "keep the overall documentation system legible from one entry page",
            "avoid collapsing all handbook responsibilities into the home page itself",
        ),
    )
    body = add_reading_advice(
        body,
        (
            "start with the repository handbook when the question spans packages",
            "move into a product package when you need ownership, interfaces, operations, or quality detail",
            "use the maintainer or compatibility sections only when the problem is explicitly about those concerns",
        ),
    )
    body = add_core_claim(
        body,
        "The root page should let a reviewer choose the right handbook path in seconds instead of forcing them to infer the documentation system from the tree layout.",
    )
    body = add_why_it_matters(
        body,
        "If this page is vague, readers enter the wrong handbook branch first and the cost of reviewing the repository rises immediately because context has to be rebuilt page by page.",
    )
    body = add_if_it_drifts(
        body,
        (
            "readers start the wrong review path and waste time rebuilding orientation",
            "the root site stops acting like the reliable front door to the repository handbook",
            "package, maintainer, and compatibility sections become harder to distinguish quickly",
        ),
    )
    body = add_representative_scenario(
        body,
        "A reviewer opens the docs with only a vague question like 'where does this change belong'. The root page should route them to the right handbook branch before they spend time reading the wrong kind of documentation.",
    )
    body = add_source_of_truth(
        body,
        (
            "`docs/index.md` and `mkdocs.yml` for the published routing structure",
            "`scripts/render_docs_catalog.py` for how that structure is generated",
            "the target handbook pages themselves for the actual subject-specific detail",
        ),
    )
    body = add_common_misreadings(
        body,
        (
            "that the root page itself should contain all of the repository detail",
            "that package, maintainer, and compatibility docs are interchangeable reading paths",
            "that the navigation tree alone is enough without explicit routing guidance",
        ),
    )
    body = add_next_checks(
        body,
        (
            "open the repository handbook when the question spans packages or schemas",
            "open a product package handbook when the question is about ownership or package behavior",
            "open the maintainer or compatibility handbooks only when the question is explicitly about those concerns",
        ),
    )
    body = add_update_triggers(
        body,
        (
            "the rendered handbook structure changes materially",
            "the root site stops being the fastest route into the documentation system",
            "new major sections are added or retired from the root docs tree",
        ),
    )
    body = add_anchor_section(
        body,
        (
            "`docs/index.md` as the root routing page",
            "`mkdocs.yml` as the published navigation source",
            "`scripts/render_docs_catalog.py` as the generator that shapes the docs tree",
        ),
    )
    return "\n".join(
        [
            front_matter("bijux-canon Documentation", "bijux-canon-docs", "index"),
            body,
        ]
    )


def render_root_page(
    slug: str,
    title: str,
    targets: set[str],
    categories_by_package: dict[str, tuple[str, ...]],
) -> str:
    package_links = "\n".join(
        (
            f"- [{info.title}](../{info.slug}/foundation/index.md) for {info.description.lower()}"
            if key in targets and "foundation" in categories_by_package.get(key, ())
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
    body = clean_block(bodies[slug])
    body = add_page_route_map(
        body,
        "bijux-canon",
        "Repository Handbook",
        title,
        ("package boundaries", "shared workflows", "reviewable decisions"),
        (
            ("Repository intent", ("scope", "shared ownership")),
            ("Review inputs", ("code", "schemas", "automation")),
            ("Review outputs", ("clear decisions", "stable docs")),
        ),
    )
    body = add_working_interpretation(
        body,
        "These repository pages should explain the shared monorepo frame that no single package can explain alone. They are most useful when a reader needs to reason about packages together rather than in isolation.",
    )
    body = add_reader_fit_section(
        body,
        (
            "you are dealing with repository-wide seams rather than one package alone",
            "you need shared workflow, schema, or governance context before changing code",
            "you want the monorepo view that sits above the package handbooks",
        ),
    )
    body = add_decision_rule(
        body,
        f"Use `{title}` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect rather than absorb that detail.",
    )
    body = add_what_good_looks_like(
        body,
        (
            f"`{title}` keeps repository guidance above package-local detail instead of competing with it",
            "the reader can tell which root assets matter to the topic before opening code",
            "cross-package reasoning becomes simpler because the repository frame is explicit",
        ),
    )
    body = add_question_section(
        body,
        (
            "which repository-level decision this page clarifies",
            "which shared assets or workflows a reviewer should inspect",
            "how the repository boundary differs from package-local ownership",
        ),
    )
    body = add_reviewer_lens_section(
        body,
        (
            "compare the page claims with the real root files, workflows, or schema assets",
            "check that repository guidance still stops where package ownership begins",
            "confirm that any repository rule described here is still enforceable in code or automation",
        ),
    )
    body = add_core_claim(
        body,
        "Each repository handbook page should make one monorepo-level decision legible enough that package-local pages do not need to reinvent root context.",
    )
    body = add_why_it_matters(
        body,
        "Repository pages matter because they keep shared rules, schemas, workflows, and release expectations from being rediscovered separately inside each package.",
    )
    body = add_if_it_drifts(
        body,
        (
            "root rules become folklore instead of checked-in reference",
            "packages start re-explaining shared repository behavior inconsistently",
            "reviewers lose the ability to separate monorepo policy from package-local design",
        ),
    )
    body = add_representative_scenario(
        body,
        "A cross-package change touches schemas, automation, and release behavior at once. The repository page should tell the reviewer which part of that decision belongs at the root and which part belongs back in package-local docs.",
    )
    body = add_source_of_truth(
        body,
        (
            "root files like `pyproject.toml`, `Makefile`, `makes/`, and `.github/workflows/` for actual repository behavior",
            "`apis/` for tracked shared schema artifacts",
            "this section for the explanation of how those assets fit together",
        ),
    )
    body = add_common_misreadings(
        body,
        (
            "that repository policy can be inferred safely from one package alone",
            "that root docs should silently absorb package-local details",
            "that repository guidance is authoritative without corresponding checked-in assets",
        ),
    )
    body = add_next_checks(
        body,
        (
            "move to the owning package docs when the question stops being repository-wide",
            "check root files, schemas, or workflows named here before trusting prose alone",
            "use maintainer docs next if the root issue is really about automation or drift tooling",
        ),
    )
    body = add_update_triggers(
        body,
        (
            "root workflows, schemas, or shared governance change materially",
            "repository policy moves into or out of package-local ownership",
            "the current repository explanation no longer matches checked-in root assets",
        ),
    )
    body = add_honesty_boundary(
        body,
        "These pages explain repository-level intent and shared rules, but they do not override package-local ownership or serve as evidence without the referenced files, workflows, and checks.",
    )
    if slug == "index":
        body = add_section_contract(
            body,
            (
                "define the shared monorepo boundary above any single package",
                "point readers to the package handbooks without duplicating their local detail",
                "keep root rules tied to actual repository files and automation",
            ),
        )
        body = add_reading_advice(
            body,
            (
                "read this page first when the question is about workspace structure or shared governance",
                "move to package docs when the question becomes package-specific",
                "use this section as the repository-level frame before reviewing code or schemas",
            ),
        )
    body = add_anchor_section(
        body,
        (
            "`pyproject.toml` for workspace metadata and commit conventions",
            "`Makefile` and `makes/` for root automation",
            "`apis/` and `.github/workflows/` for schema and validation review",
        ),
    )
    return "\n".join(
        [
            front_matter(title, "bijux-canon-docs", "index" if slug == "index" else "explanation"),
            body,
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
    body = clean_block(bodies[slug])
    body = add_page_route_map(
        body,
        "bijux-canon",
        "Maintainer Handbook",
        title,
        ("quality gates", "schema governance", "release support"),
        (
            ("Maintainer role", ("quality", "security")),
            ("Repository health", ("schemas", "supply chain")),
            ("Operational outcome", ("release clarity", "package consistency")),
        ),
    )
    body = add_working_interpretation(
        body,
        "These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they reduce hidden automation and make package-wide maintenance effects inspectable.",
    )
    body = add_reader_fit_section(
        body,
        (
            "you are changing repository automation, validation, or release support",
            "you need maintainer-only context that should not live in product package docs",
            "you are reviewing CI, schema drift, or supply-chain behavior",
        ),
    )
    body = add_decision_rule(
        body,
        f"Use `{title}` to decide whether a change belongs to maintainer automation or to a product package contract. If the change would affect end-user behavior directly, this page should push the review back toward the owning product package instead of letting maintainer scope sprawl.",
    )
    body = add_what_good_looks_like(
        body,
        (
            f"`{title}` makes maintainer-only behavior explicit enough that it does not surprise contributors",
            "the page distinguishes repository-health work from runtime product behavior cleanly",
            "automation intent stays understandable without digging through CI and helpers first",
        ),
    )
    body = add_question_section(
        body,
        (
            "which repository maintenance concern this page explains",
            "which maintainer modules or tests support that concern",
            "what a reviewer should confirm before changing repository automation",
        ),
    )
    body = add_reviewer_lens_section(
        body,
        (
            "compare the described maintainer behavior with the actual helper modules and tests",
            "check that maintainer-only guidance has not leaked into product-facing pages",
            "confirm that repository automation still names its package impact explicitly",
        ),
    )
    body = add_core_claim(
        body,
        "Each maintainer page should explain repository-health behavior in a way that is explicit, testable, and clearly separate from end-user product behavior.",
    )
    body = add_why_it_matters(
        body,
        "Maintainer pages matter because hidden automation is one of the fastest ways for a monorepo to become hard to trust, hard to change, and hard to release safely.",
    )
    body = add_if_it_drifts(
        body,
        (
            "maintainer-only behavior becomes harder to discover before it surprises a contributor",
            "repository automation changes without a stable explanation of its intent",
            "product docs get polluted with infrastructure concerns that belong elsewhere",
        ),
    )
    body = add_representative_scenario(
        body,
        "A CI or release helper changes behavior and a contributor needs to know whether the effect is repository maintenance only or whether it changes a product package contract. This section should make that distinction fast.",
    )
    body = add_source_of_truth(
        body,
        (
            "`packages/bijux-canon-dev/src/bijux_canon_dev` for implemented maintainer helpers",
            "`packages/bijux-canon-dev/tests` for executable proof of maintainer behavior",
            "this section for the maintained explanation of maintainer intent",
        ),
    )
    body = add_common_misreadings(
        body,
        (
            "that maintainer automation belongs in product package docs",
            "that CI behavior is self-explanatory without maintainer documentation",
            "that repository-health tools are part of the public runtime product surface",
        ),
    )
    body = add_next_checks(
        body,
        (
            "move to product package docs if the question is user-facing behavior rather than repository health",
            "open the relevant helper module or test after using this page to orient yourself",
            "return to repository handbook pages when the maintainer issue turns out to be root policy instead",
        ),
    )
    body = add_update_triggers(
        body,
        (
            "maintainer helpers, tests, or CI integrations change materially",
            "repository-health work moves across package boundaries",
            "the section stops matching the actual maintainer-only operating model",
        ),
    )
    body = add_honesty_boundary(
        body,
        "This section can describe maintainer automation and repository health work, but it should never imply that maintainer tooling is part of the end-user product surface.",
    )
    if slug == "index":
        body = add_section_contract(
            body,
            (
                "explain repository maintenance behavior without turning it into product documentation",
                "tie maintainer claims to helper modules, tests, and workflows",
                "keep automation boundaries explicit enough to review safely",
            ),
        )
        body = add_reading_advice(
            body,
            (
                "start here when the change affects CI, release support, schema drift, or repository health checks",
                "return to product package docs when the issue is user-facing behavior",
                "use this section to separate maintainer intent from runtime intent",
            ),
        )
    body = add_anchor_section(
        body,
        (
            "`packages/bijux-canon-dev/src/bijux_canon_dev` for maintainer helpers",
            "`packages/bijux-canon-dev/tests` for executable maintenance proof",
            "`apis/` and root workflows for repository-level integration points",
        ),
    )
    return "\n".join(
        [
            front_matter(title, "bijux-canon-dev-docs", "index" if slug == "index" else "explanation"),
            body,
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
    body = clean_block(bodies[slug])
    body = add_page_route_map(
        body,
        "bijux-canon",
        "Compatibility Handbook",
        title,
        ("legacy package names", "migration decisions", "retirement review"),
        (
            ("Legacy surface", ("distribution names", "import names")),
            ("Canonical target", ("current packages", "new work")),
            ("Decision pressure", ("migration", "retirement")),
        ),
    )
    body = add_working_interpretation(
        body,
        "These compatibility pages should make legacy names understandable without romanticizing them. Their value is in clarifying preservation, migration, and retirement pressure with as little ambiguity as possible.",
    )
    body = add_reader_fit_section(
        body,
        (
            "you are tracing a legacy package name back to its canonical replacement",
            "you need migration guidance rather than product implementation detail",
            "you are deciding whether a compatibility surface still deserves to exist",
        ),
    )
    body = add_decision_rule(
        body,
        f"Use `{title}` to decide whether a preserved legacy name is still serving a real migration need. If the only reason to keep it is habit rather than an identified dependent environment, the section should bias the reviewer toward migration or retirement planning.",
    )
    body = add_what_good_looks_like(
        body,
        (
            f"`{title}` makes the legacy-to-canonical path obvious",
            "migration pressure is clearer than nostalgia for old package names",
            "retirement can be discussed from evidence rather than from vague discomfort",
        ),
    )
    body = add_question_section(
        body,
        (
            "which legacy surface is still preserved",
            "when new work should move to the canonical package instead",
            "what evidence would justify retiring a compatibility package",
        ),
    )
    body = add_reviewer_lens_section(
        body,
        (
            "compare legacy names here with the compatibility package metadata and README targets",
            "check that migration advice still points at current canonical docs",
            "confirm that compatibility language does not accidentally encourage new work to start here",
        ),
    )
    body = add_core_claim(
        body,
        "Each compatibility page should make migration pressure clearer than legacy habit, so preserved names remain understandable without becoming a second product line.",
    )
    body = add_why_it_matters(
        body,
        "Compatibility pages matter because legacy package names often survive longer than the people who remember why they exist, and that makes migration drift expensive.",
    )
    body = add_if_it_drifts(
        body,
        (
            "legacy names become easier to keep using than to migrate away from",
            "canonical targets become ambiguous in old automation or docs",
            "retirement decisions get delayed because the actual migration state is unclear",
        ),
    )
    body = add_representative_scenario(
        body,
        "A legacy dependency name appears in an old environment file. The compatibility docs should let a maintainer map it to the canonical package and judge whether that old name still deserves to survive.",
    )
    body = add_source_of_truth(
        body,
        (
            "the `packages/compat-*` metadata and README files for preserved legacy surfaces",
            "the matching canonical package docs for current behavior",
            "this section for the migration and retirement explanation that ties them together",
        ),
    )
    body = add_common_misreadings(
        body,
        (
            "that legacy names are still the preferred public names",
            "that compatibility packages should grow like first-class product packages",
            "that preserved import or distribution names prove long-term architectural importance",
        ),
    )
    body = add_next_checks(
        body,
        (
            "move to the canonical package docs once the current target package is known",
            "inspect compatibility package metadata if the question is about what remains preserved",
            "use this section again only when evaluating migration progress or retirement readiness",
        ),
    )
    body = add_update_triggers(
        body,
        (
            "a legacy package is added, retired, or repointed to a different canonical target",
            "migration guidance becomes stale compared with the current package set",
            "compatibility scope changes materially enough to affect retirement decisions",
        ),
    )
    body = add_honesty_boundary(
        body,
        "This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth.",
    )
    if slug == "index":
        body = add_section_contract(
            body,
            (
                "record which legacy package names remain supported",
                "make migration guidance faster than guessing from old names",
                "keep retirement decisions tied to explicit evidence rather than habit",
            ),
        )
        body = add_reading_advice(
            body,
            (
                "start here when you encounter a legacy package name in old automation or documentation",
                "move to the canonical package docs once you know the current target",
                "use this section to evaluate whether a compatibility surface should remain",
            ),
        )
    body = add_anchor_section(
        body,
        (
            "`packages/compat-*` for the preserved legacy packages",
            "the compatibility package `README.md` files for canonical targets",
            "the matching canonical package docs for current behavior and new work",
        ),
    )
    return "\n".join(
        [
            front_matter(title, "bijux-canon-compat-docs", "index" if slug == "index" else "explanation"),
            body,
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


def related_links(package: PackageInfo, category: str, active_categories: tuple[str, ...]) -> str:
    section_links = []
    for other in active_categories:
        if other == category:
            continue
        section_links.append(f"- [{other.title()}](../{other}/index.md)")
    return "\n".join(section_links)


def render_package_page(
    package: PackageInfo,
    category: str,
    slug: str,
    title: str,
    active_categories: tuple[str, ...],
) -> str:
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

            {related_links(package, category, active_categories)}

            ## Purpose

            This page explains how to use the {category} section for `{package.title}` without repeating the detail that belongs on the topic pages beneath it.

            ## Stability

            This page is part of the canonical package docs spine. Keep it aligned with the current package boundary and the topic pages in this section.
            """
        )
    else:
        body = render_package_topic(package, category, slug, title, package_root)
    body = clean_block(body)
    body = add_page_route_map(
        body,
        package.title,
        category.title(),
        title,
        ("reviewable boundaries", "operator clarity", "change safety"),
        (
            (
                "Owned package surface",
                (package.owns[0], package.owns[1] if len(package.owns) > 1 else package.owns[0]),
            ),
            (
                "Evidence to inspect",
                (
                    package.modules[0][0],
                    package.artifacts[0],
                ),
            ),
            (
                "Review pressure",
                (
                    category.title(),
                    package.tests[0],
                ),
            ),
        ),
    )
    body = add_working_interpretation(body, package_working_interpretation(package, category))
    body = add_reader_fit_section(body, package_page_reader_fit(package, category))
    body = add_decision_rule(body, package_decision_rule(package, category, title))
    body = add_what_good_looks_like(body, package_what_good_looks_like(package, category, title))
    body = add_core_claim(body, package_core_claim(package, category))
    body = add_why_it_matters(body, package_why_it_matters(package, category))
    body = add_if_it_drifts(body, package_if_it_drifts(package, category))
    body = add_representative_scenario(body, package_scenario(package, category))
    body = add_source_of_truth(body, package_source_of_truth(package, category))
    body = add_common_misreadings(body, package_common_misreadings(package, category))
    body = add_anchor_section(body, package_anchor_bullets(package, category))
    body = add_next_checks(body, package_next_checks(package, category))
    body = add_update_triggers(body, package_update_triggers(package, category))
    body = add_question_section(body, package_page_questions(package, category, title))
    body = add_reviewer_lens_section(body, package_page_reviewer_lens(package, category))
    body = add_honesty_boundary(body, package_honesty_boundary(package, category))
    if slug == "index":
        body = add_section_contract(
            body,
            (
                f"define what the {category} section covers for {package.title}",
                "point readers to the topic pages that hold the detailed explanations",
                "keep the section boundary reviewable as the package evolves",
            ),
        )
        body = add_reading_advice(
            body,
            (
                "start here when you know the package but not yet the right page inside the section",
                "use the page list to choose the narrowest topic that matches the current question",
                "move across sections only after this section stops being the right lens",
            ),
        )
    return "\n".join(
        [
            front_matter(title, package.owner, "index" if slug == "index" else "explanation"),
            body,
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


def write_platform_docs(
    targets: set[str],
    categories_by_package: dict[str, tuple[str, ...]],
) -> None:
    write_doc(DOCS_ROOT / "index.md", render_home(targets, categories_by_package))
    base = DOCS_ROOT / "bijux-canon"
    for slug, title in ROOT_PAGES:
        write_doc(
            base / f"{slug}.md",
            render_root_page(slug, title, targets, categories_by_package),
        )


def write_package_docs(package_key: str, active_categories: tuple[str, ...]) -> None:
    package = PRODUCT_PACKAGES[package_key]
    base = DOCS_ROOT / package.slug
    for category in active_categories:
        for slug, title in PACKAGE_CATEGORY_PAGES[category]:
            write_doc(
                base / category / f"{slug}.md",
                render_package_page(package, category, slug, title, active_categories),
            )


def write_dev_docs() -> None:
    base = DOCS_ROOT / "bijux-canon-dev"
    for slug, title in DEV_PAGES:
        write_doc(base / f"{slug}.md", render_dev_page(slug, title))


def write_compat_docs() -> None:
    base = DOCS_ROOT / "compat-packages"
    for slug, title in COMPAT_PAGES:
        write_doc(base / f"{slug}.md", render_compat_page(slug, title))


def nav_lines(
    targets: set[str],
    categories_by_package: dict[str, tuple[str, ...]],
) -> list[str]:
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
        package_categories = categories_by_package.get(key, ())
        lines.append(f"  - {package.title}:")
        for category in package_categories:
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


def write_mkdocs(
    targets: set[str],
    categories_by_package: dict[str, tuple[str, ...]],
) -> None:
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
            *nav_lines(targets, categories_by_package),
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


def validate_rendered_docs() -> None:
    required_headings = (
        "## Page Maps",
        "## Core Claim",
        "## Why It Matters",
        "## If It Drifts",
        "## Representative Scenario",
        "## Source Of Truth Order",
        "## Common Misreadings",
        "## Concrete Anchors",
        "## Use This Page When",
        "## Next Checks",
        "## Update This Page When",
        "## What This Page Answers",
        "## Reviewer Lens",
        "## Honesty Boundary",
        "## Purpose",
        "## Stability",
    )
    failures: list[str] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.count("```mermaid") < 2:
            failures.append(f"{path}: fewer than two Mermaid diagrams")
        for heading in required_headings:
            if heading not in text:
                failures.append(f"{path}: missing heading {heading}")
        if text.count("- ") < 18:
            failures.append(f"{path}: too few bullet points for current handbook depth standard")
        word_count = len(text.split())
        if word_count < 260:
            failures.append(f"{path}: too few words for current handbook depth standard ({word_count})")
    if failures:
        joined = "\n".join(failures[:50])
        raise RuntimeError(f"Rendered docs validation failed:\n{joined}")


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
    parser.add_argument(
        "--product-categories",
        nargs="+",
        choices=PACKAGE_CATEGORY_ORDER,
        default=PACKAGE_CATEGORY_ORDER,
        help="Package categories to render for product packages.",
    )
    parser.add_argument(
        "--categories-for",
        action="append",
        default=[],
        metavar="PACKAGE=CATEGORY1,CATEGORY2",
        help="Override rendered categories for one product package.",
    )
    return parser.parse_args()


def parse_category_overrides(values: list[str]) -> dict[str, tuple[str, ...]]:
    overrides: dict[str, tuple[str, ...]] = {}
    for value in values:
        if "=" not in value:
            raise ValueError(
                f"Invalid --categories-for value '{value}'. Expected PACKAGE=CAT1,CAT2."
            )
        package_key, raw_categories = value.split("=", 1)
        if package_key not in PRODUCT_PACKAGES:
            raise ValueError(f"Unknown product package '{package_key}'.")
        categories = tuple(item.strip() for item in raw_categories.split(",") if item.strip())
        invalid = [item for item in categories if item not in PACKAGE_CATEGORY_ORDER]
        if invalid:
            raise ValueError(
                f"Invalid categories for {package_key}: {', '.join(invalid)}"
            )
        overrides[package_key] = categories
    return overrides


def main() -> None:
    args = parse_args()
    targets = set(args.targets or TARGET_ORDER)
    product_categories = tuple(args.product_categories)
    category_overrides = parse_category_overrides(args.categories_for)
    categories_by_package = {
        key: category_overrides.get(key, product_categories)
        for key in PRODUCT_PACKAGES
    }
    clean_docs_root()
    if "platform" in targets:
        write_platform_docs(targets, categories_by_package)
    for key in ("ingest", "index", "reason", "agent", "runtime"):
        if key in targets:
            write_package_docs(key, categories_by_package[key])
    if "dev" in targets:
        write_dev_docs()
    if "compat" in targets:
        write_compat_docs()
    if not (DOCS_ROOT / "index.md").exists():
        write_doc(DOCS_ROOT / "index.md", render_home(targets, categories_by_package))
    else:
        write_doc(DOCS_ROOT / "index.md", render_home(targets, categories_by_package))
    write_mkdocs(targets, categories_by_package)
    validate_rendered_docs()
    count = len(list(DOCS_ROOT.rglob("*.md")))
    print(f"Rendered {count} Markdown files for targets: {', '.join(sorted(targets))}")


if __name__ == "__main__":
    main()
