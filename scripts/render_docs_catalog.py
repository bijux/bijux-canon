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
            f"what problem `{package.title}` is supposed to own on purpose",
            "where the package boundary stops, even when nearby code looks tempting",
            "which neighboring package seams deserve comparison before the boundary is changed",
        ),
        "architecture": (
            f"how `{package.title}` is organized internally in terms a reviewer can follow",
            "which modules carry the main execution and dependency story",
            "where structural drift would show up before it becomes expensive",
        ),
        "interfaces": (
            f"which public or operator-facing surfaces `{package.title}` is really asking readers to trust",
            "which schemas, artifacts, imports, or commands behave like contracts",
            "what compatibility pressure a change to this surface would create",
        ),
        "operations": (
            f"how `{package.title}` is installed, run, diagnosed, and released in practice",
            "which checked-in files and tests anchor the operational story",
            "where a maintainer should look first when the package behaves differently",
        ),
        "quality": (
            f"what currently proves the `{package.title}` contract instead of merely describing it",
            "which risks, limits, and assumptions still need explicit skepticism",
            "what a reviewer should be able to say before accepting a change as done",
        ),
    }
    return question_map[category]


def package_page_reader_fit(
    package: PackageInfo,
    category: str,
) -> tuple[str, ...]:
    fit_map = {
        "foundation": (
            "you need the package idea before the implementation detail",
            "you are deciding whether work belongs here or in a neighboring package",
            "you want the shortest honest explanation of what this package is for",
        ),
        "architecture": (
            "you are tracing structure, execution flow, or dependency pressure",
            "you need to understand how modules fit before refactoring",
            "you are reviewing design drift rather than one isolated bug",
        ),
        "interfaces": (
            "you need the public command, API, import, schema, or artifact surface",
            "you are checking whether a caller can safely rely on a given entrypoint or shape",
            "you want the contract-facing side of the package before building on it",
        ),
        "operations": (
            "you are installing, running, diagnosing, or releasing the package",
            "you need repeatable operational anchors rather than architectural framing",
            "you are responding to package behavior in local work, CI, or incident pressure",
        ),
        "quality": (
            "you are reviewing tests, invariants, limitations, or ongoing risks",
            "you need evidence that the documented contract is actually defended",
            "you are deciding whether a change is truly done rather than merely implemented",
        ),
    }
    return fit_map[category]


def package_page_reviewer_lens(
    package: PackageInfo,
    category: str,
) -> tuple[str, ...]:
    lens_map = {
        "foundation": (
            "compare the stated boundary with the modules, artifacts, and tests that are supposed to uphold it",
            "check that out-of-scope behavior is not quietly re-entering through convenience paths",
            "confirm that the package story still matches the real repository layout and neighboring package docs",
        ),
        "architecture": (
            "trace the described execution path through the named modules instead of trusting the diagram alone",
            "look for dependency direction or layering that now contradicts the documented seam",
            "verify that the structural risks named here still match the current code shape",
        ),
        "interfaces": (
            "compare commands, schemas, imports, and artifacts against the documented surface one by one",
            "check whether a seemingly local change actually needs compatibility review",
            "confirm that examples still point to real entrypoints and not to stale habits",
        ),
        "operations": (
            "verify that setup, workflow, and release statements still match package metadata and current commands",
            "check that operational guidance still points at real diagnostics and validation paths",
            "confirm that maintainer advice still works under current local and CI expectations",
        ),
        "quality": (
            "compare the documented proof story with the actual test layout and release posture",
            "look for limitations or risks that should have moved with recent behavior changes",
            "verify that the claimed done-ness standard still reflects real validation practice",
        ),
    }
    return lens_map[category]


def package_honesty_boundary(package: PackageInfo, category: str) -> str:
    honesty_map = {
        "foundation": (
            f"This page can explain the intended boundary of `{package.title}`, but it"
            " cannot prove that boundary by itself. The real proof still lives in the"
            " code, tests, and neighboring package seams that either support or contradict"
            " the story told here."
        ),
        "architecture": (
            f"This page describes the current structural model of `{package.title}`, but it"
            " does not guarantee that every import path or runtime path still obeys that"
            " model. Readers should treat it as a map that must stay aligned with code and"
            " tests, not as an authority above them."
        ),
        "interfaces": (
            f"This page can identify the intended public surfaces of `{package.title}`, but"
            " real compatibility depends on code, schemas, artifacts, examples, and tests"
            " staying aligned. If those disagree, the prose is wrong or incomplete."
        ),
        "operations": (
            f"This page explains how `{package.title}` is expected to be operated, but it"
            " does not replace package metadata, actual runtime behavior, or validation in"
            " a real environment. A workflow is only trustworthy if a maintainer can still"
            " repeat it from the checked-in assets named here."
        ),
        "quality": (
            f"This page explains how `{package.title}` is supposed to earn trust, but it"
            " does not claim that prose alone is enough. If the listed tests, checks, and"
            " review practice stop backing the story, the story has to change."
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
            f"The core foundational claim of `{package.title}` is that its ownership can be"
            " explained as a deliberate package boundary, not as an accident of where code"
            " happened to accumulate."
        ),
        "architecture": (
            f"The core architectural claim of `{package.title}` is that its structure is"
            " deliberate enough for a reviewer to trace responsibilities, dependencies, and"
            " drift pressure without reverse-engineering the whole codebase."
        ),
        "interfaces": (
            f"The core interface claim of `{package.title}` is that commands, APIs,"
            " imports, schemas, and artifacts form a reviewable contract rather than a set"
            " of implied habits."
        ),
        "operations": (
            f"The core operational claim of `{package.title}` is that install, run,"
            " diagnose, and release paths can be repeated from explicit package assets"
            " instead of oral history."
        ),
        "quality": (
            f"The core quality claim of `{package.title}` is that tests, invariants,"
            " visible risks, and completion criteria jointly show whether the package is"
            " trustworthy after change."
        ),
    }
    return claim_map[category]


def package_why_it_matters(package: PackageInfo, category: str) -> str:
    matter_map = {
        "foundation": (
            f"If the foundation pages for `{package.title}` are weak, reviewers stop"
            " knowing where the package really begins and ends. Adjacent packages then"
            " absorb behavior by convenience instead of by design."
        ),
        "architecture": (
            f"If the architecture pages for `{package.title}` are weak, refactors become"
            " guesswork. Dependency drift can hide until it leaks into tests, caller"
            " behavior, or operator experience."
        ),
        "interfaces": (
            f"If the interface pages for `{package.title}` are weak, callers cannot tell"
            " which surfaces are stable enough to depend on. Compatibility review then"
            " arrives after people have already built on the wrong assumptions."
        ),
        "operations": (
            f"If the operations pages for `{package.title}` are weak, maintainers end up"
            " relearning install, diagnosis, and release from trial and error instead of"
            " from checked-in package truth."
        ),
        "quality": (
            f"If the quality pages for `{package.title}` are weak, it becomes difficult"
            " to tell whether a change is genuinely safe or merely passes a narrow local"
            " check."
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
            f"`{package.package_dir}/tests` for executable proof that the boundary still holds under change",
            f"`{package.package_dir}/README.md` plus this section for the shortest maintained explanation of that boundary",
        ),
        "architecture": (
            f"`{package.package_dir}/src/{package.import_name}` for the actual dependency direction and module structure",
            f"`{package.package_dir}/tests` for structural and behavioral regressions that reveal drift",
            "this page for the reviewer-facing map that should stay aligned with those assets",
        ),
        "interfaces": (
            f"`{package.package_dir}/src/{package.import_name}` for the implemented interface boundary",
            *(f"`{item}` as tracked contract evidence for caller-facing behavior" for item in package.api_specs[:1]),
            f"`{package.package_dir}/tests` for compatibility and behavior proof",
        ),
        "operations": (
            f"`{package.package_dir}/pyproject.toml` for install and release metadata that a maintainer can actually execute against",
            f"`{package.package_dir}/README.md` and package tests for the shortest checked-in operator truth",
            "this page for the repeatable workflow narrative that should match those assets rather than drift away from them",
        ),
        "quality": (
            f"`{package.package_dir}/tests` for executable proof",
            f"`{package.package_dir}/pyproject.toml` and release notes for declared constraints and change posture",
            "this page for the review lens that explains how to interpret that proof honestly",
        ),
    }
    return tuple(truth_map[category])


def package_common_misreadings(package: PackageInfo, category: str) -> tuple[str, ...]:
    misreading_map = {
        "foundation": (
            f"that `{package.title}` owns any nearby behavior just because it would be convenient",
            "that a boundary statement is enough even when code and tests tell a different story",
            "that out-of-scope means unimportant rather than intentionally owned elsewhere",
        ),
        "architecture": (
            "that the documented module map guarantees every import is still clean automatically",
            "that the most visible current path is the whole architectural contract",
            "that diagrams excuse the reader from checking the named modules and tests",
        ),
        "interfaces": (
            "that every visible package surface is equally stable",
            "that one schema file or example captures the whole compatibility story",
            "that interface prose overrides code, artifacts, or tests when they disagree",
        ),
        "operations": (
            "that the shortest operator path is always the most authoritative source of truth",
            "that setup or release behavior can be inferred safely without checking package metadata",
            "that one successful local run proves the whole operational contract is intact",
        ),
        "quality": (
            "that a passing local test automatically satisfies the package review standard",
            "that documented risks stay valid even when the code and interfaces have changed around them",
            "that done-ness is only about implementation and not about proof, clarity, and release impact",
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
            " self-description. They should let a reader understand the package without"
            " needing to reconstruct its purpose from recent implementation history."
        ),
        "architecture": (
            f"Read the {category} pages for `{package.title}` as a reviewer-facing map"
            " of structure and flow. They should shorten code reading, not try to replace"
            " it, and they should make drift visible before it becomes surprising."
        ),
        "interfaces": (
            f"Read the {category} pages for `{package.title}` as the bridge between"
            " implementation and caller expectation. They should tell a reader what the"
            " package is prepared to stand behind before a downstream dependency forms."
        ),
        "operations": (
            f"Read the {category} pages for `{package.title}` as the package's explicit"
            " operating memory. They should make common tasks repeatable without forcing"
            " maintainers to relearn the workflow from code, CI logs, or oral history."
        ),
        "quality": (
            f"Read the {category} pages for `{package.title}` as the proof frame around"
            " the package. They should explain how trust is earned, how risk stays"
            " visible, and why a passing local check is not always enough."
        ),
    }
    return interpretation_map[category]


def package_decision_rule(package: PackageInfo, category: str, title: str) -> str:
    rule_map = {
        "foundation": (
            f"Use `{title}` to decide whether a change makes `{package.title}` easier or harder to defend as a bounded package. "
            "If the work expands package authority without making ownership clearer, stop and re-check the boundary before treating the change as a local improvement."
        ),
        "architecture": (
            f"Use `{title}` to decide whether a structural change makes `{package.title}` easier or harder to explain in terms of modules, dependency direction, and execution flow. "
            "If the change works only because the design becomes harder to read, the safer answer is redesign rather than acceptance."
        ),
        "interfaces": (
            f"Use `{title}` to decide whether a caller-facing surface is explicit enough to depend on. "
            "If the surface cannot be tied back to concrete code, schemas, artifacts, examples, and tests, treat it as unstable until that evidence is visible."
        ),
        "operations": (
            f"Use `{title}` to decide whether a maintainer can repeat the package workflow from checked-in assets instead of memory. "
            "If a step works only because someone already knows the trick, the workflow is not documented clearly enough yet."
        ),
        "quality": (
            f"Use `{title}` to decide whether `{package.title}` has actually earned trust after a change. "
            "If one narrow green check hides a wider contract, risk, or validation gap, the work is not done yet."
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


def package_failure_signals(package: PackageInfo, category: str, title: str) -> tuple[str, ...]:
    signal_map = {
        "foundation": (
            f"`{title}` has to explain the same ownership claim with repeated exceptions",
            "the out-of-scope list starts looking like shadow ownership instead of a real boundary",
            "review conversations keep falling back to package adjacency rather than package intent",
        ),
        "architecture": (
            f"`{title}` points to modules that no longer carry the behavior the page claims they do",
            "dependency direction has to be explained with caveats instead of a clean structural story",
            "the path from interface to domain to proof no longer feels traceable in one pass",
        ),
        "interfaces": (
            f"`{title}` names surfaces that cannot be matched to real code, schemas, or artifacts",
            "callers have to infer stability from examples instead of from explicit contract evidence",
            "compatibility review starts after change has already landed instead of before",
        ),
        "operations": (
            f"`{title}` only works if the maintainer already knows unstated steps",
            "package metadata, runtime behavior, and operational docs start telling different stories",
            "incident handling requires reverse-engineering workflow from code instead of following checked-in guidance",
        ),
        "quality": (
            f"`{title}` says the package is protected but cannot show which proof closes which risk",
            "reviewers disagree on whether the work is done because the standard is too implicit",
            "limitations remain unchanged even when package behavior has obviously shifted",
        ),
    }
    return signal_map[category]


def package_cross_implications(package: PackageInfo, category: str) -> tuple[str, ...]:
    implication_map = {
        "foundation": (
            f"changes here influence how neighboring packages are allowed to stay narrow around `{package.title}`",
            "a weak boundary explanation raises architectural and quality ambiguity immediately",
            "interface and operations pages inherit confusion when foundational ownership is unclear",
        ),
        "architecture": (
            f"changes here alter how interface, operations, and quality pages for `{package.title}` should be read",
            "structural drift often becomes visible in caller-facing seams before it is obvious in prose",
            "quality expectations need to move when the architecture adds new execution or dependency pressure",
        ),
        "interfaces": (
            f"changes here shape what downstream packages and operators can safely assume about `{package.title}`",
            "operations and quality pages become stale quickly if contract surfaces move silently",
            "architectural seams need review whenever a new public surface appears for convenience",
        ),
        "operations": (
            f"changes here affect how maintainers and CI interact with `{package.title}` across environments",
            "interface expectations often surface again as operational preconditions or diagnostics",
            "quality pages must evolve when the operational path changes what counts as sufficient validation",
        ),
        "quality": (
            f"changes here influence how all other `{package.title}` sections should be trusted after modification",
            "foundation, architecture, interface, and operations claims all become weaker if proof expectations drift",
            "review discipline here determines whether neighboring sections remain explanatory or merely aspirational",
        ),
    }
    return implication_map[category]


def package_evidence_checklist(package: PackageInfo, category: str) -> tuple[str, ...]:
    checklist_map = {
        "foundation": (
            f"read the owned module roots under `{package.package_dir}/src/{package.import_name}` with the boundary statement in mind",
            f"inspect `{package.package_dir}/tests` for proof that the boundary is enforced instead of merely described",
            "check whether adjacent package docs now tell a conflicting ownership story",
        ),
        "architecture": (
            f"open the listed structural modules in `{package.package_dir}/src/{package.import_name}` and trace whether they still match the page narrative",
            f"inspect `{package.package_dir}/tests` for regressions that reveal changed execution or dependency structure",
            "compare the documented hotspots with the actual changed files in the review",
        ),
        "interfaces": (
            f"inspect the implemented interface modules under `{package.package_dir}/src/{package.import_name}`",
            *(f"review `{item}` as tracked contract evidence" for item in package.api_specs[:1]),
            f"run through `{package.package_dir}/tests` or equivalent proofs that protect the surface",
        ),
        "operations": (
            f"verify `{package.package_dir}/pyproject.toml` and `{package.package_dir}/README.md` still match the operational story",
            f"inspect `{package.package_dir}/tests` for the workflow or environment proof the page implies",
            "compare the documented operating path with the actual steps needed in local or CI use",
        ),
        "quality": (
            f"read `{package.package_dir}/tests` with the page's proof claims in hand",
            f"verify package metadata and release notes in `{package.package_dir}` do not contradict the review standard",
            "check whether known limitations, risks, and completion language all moved together in the current change",
        ),
    }
    return tuple(checklist_map[category])


def package_antipatterns(package: PackageInfo, category: str) -> tuple[str, ...]:
    antipattern_map = {
        "foundation": (
            "using package adjacency as a substitute for package ownership",
            "letting boundary exceptions accumulate until they become the real rule",
            "writing boundary prose that cannot be checked against code or tests",
        ),
        "architecture": (
            "explaining structure with diagrams that no longer match the modules listed",
            "treating temporary implementation shortcuts as if they were enduring architectural seams",
            "allowing dependency direction to drift because the code still happens to run",
        ),
        "interfaces": (
            "treating convenience surfaces as if they were deliberate contracts",
            "changing schemas or artifacts without a caller-facing compatibility discussion",
            "using examples to imply stability that code and tests do not actually promise",
        ),
        "operations": (
            "relying on tribal memory for steps that should live in checked-in assets",
            "documenting the happy path while leaving diagnostics and failure handling implicit",
            "letting release or setup guidance drift away from package metadata",
        ),
        "quality": (
            "equating one local pass with full contract confidence",
            "keeping old risk prose after the code and tests have materially changed",
            "treating definition-of-done language as ceremonial rather than operational",
        ),
    }
    return antipattern_map[category]


def package_escalate_when(package: PackageInfo, category: str) -> tuple[str, ...]:
    escalate_map = {
        "foundation": (
            "the page can no longer explain ownership without repeated cross-package caveats",
            "a change proposal would shift authority between packages rather than stay local",
            "tests and docs disagree on who is supposed to own the behavior",
        ),
        "architecture": (
            "the documented structure no longer matches the changed execution path",
            "a local refactor introduces a dependency direction question that affects other sections",
            "the review cannot explain the change without redefining a major seam",
        ),
        "interfaces": (
            "a supposedly local change alters a caller-visible schema, artifact, import, or command contract",
            "compatibility risk extends beyond one implementation file",
            "operators or downstream packages would need to relearn the surface after the change",
        ),
        "operations": (
            "the operational path changes enough to affect CI, releases, or another package's expectations",
            "the documented workflow depends on environment assumptions that are no longer stable",
            "incident or release handling can no longer be explained as a package-local concern",
        ),
        "quality": (
            "the proof story can no longer be updated without revisiting adjacent sections",
            "a local validation gap reveals a larger boundary or architecture issue",
            "reviewers cannot agree on done-ness because the underlying contract changed",
        ),
    }
    return escalate_map[category]


def package_tradeoffs(package: PackageInfo, category: str) -> tuple[str, ...]:
    tradeoff_map = {
        "foundation": (
            "prefer clean ownership over local convenience, even when nearby code looks easier to reuse",
            "prefer an explicit boundary gap over a shadow responsibility that no package clearly owns",
            f"prefer keeping `{package.title}` intelligible as a bounded package over making it look universally useful",
        ),
        "architecture": (
            "prefer clean dependency direction over short-term coupling that makes one change easier today",
            "prefer an execution path that can be explained quickly over indirection that only looks flexible",
            f"prefer structural legibility in `{package.title}` over squeezing unrelated behavior into the same module seam",
        ),
        "interfaces": (
            "prefer a smaller explicit contract over a wider surface whose stability has to be guessed",
            "prefer paying compatibility-review cost up front over discovering caller breakage after release",
            f"prefer contract evidence that is slightly heavier to maintain over allowing `{package.title}` surfaces to drift silently",
        ),
        "operations": (
            "prefer repeatable checked-in workflows over locally optimized shortcuts",
            "prefer diagnosability over hiding operational seams that matter during incidents",
            f"prefer keeping `{package.title}` operational memory visible in metadata, docs, and tests over relying on maintainer recall",
        ),
        "quality": (
            "prefer broader proof over narrower green checks when the package contract is larger than one code path",
            "prefer visible limitations over a cleaner story that hides risk",
            f"prefer a slightly slower approval path over granting `{package.title}` trust without enough evidence",
        ),
    }
    return tradeoff_map[category]


def package_approval_questions(
    package: PackageInfo, category: str, title: str
) -> tuple[str, ...]:
    approval_map = {
        "foundation": (
            f"does `{title}` still let a reviewer state `{package.title}` ownership in one clear sentence",
            "does the change preserve package boundaries without creating shadow scope in a neighbor",
            "is there concrete code and test evidence behind the boundary claim, or only persuasive prose",
        ),
        "architecture": (
            f"does `{title}` still describe a structure that a reviewer can trace without caveats",
            "is dependency direction cleaner or at least no less legible after the change",
            "can the claimed execution path still be matched to concrete modules, seams, and proof assets",
        ),
        "interfaces": (
            f"does `{title}` name only caller-facing surfaces that have explicit contract evidence",
            "would a downstream consumer understand the compatibility expectations before depending on the surface",
            "are code, schemas, artifacts, examples, and tests still telling the same contract story",
        ),
        "operations": (
            f"does `{title}` leave a maintainer able to repeat the workflow from checked-in assets",
            "are install, diagnostics, and release statements still aligned with package metadata and tests",
            "would this workflow still hold up under time pressure without hidden operator memory",
        ),
        "quality": (
            f"does `{title}` show enough proof to trust `{package.title}` after change",
            "have limitations and known risks moved with the code rather than staying stale",
            "does the acceptance bar protect the package contract rather than only one local behavior",
        ),
    }
    return approval_map[category]


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
            "Use these points as the fast check for whether the page is doing real explanatory work.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Core Claim", block)


def add_failure_signals(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Failure Signals",
            "",
            "These are the quickest signs that the page is drifting from honest explanation into noise or stale certainty.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "If It Drifts", block)


def add_cross_implications(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Cross Implications",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Source Of Truth Order", block)


def add_evidence_checklist(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Evidence Checklist",
            "",
            "Check these assets before trusting the prose. They are the concrete places where the page either holds up or falls apart.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Reviewer Lens", block)


def add_antipatterns(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Anti-Patterns",
            "",
            "These patterns make documentation feel fuller while quietly making it less clear, less honest, or less durable.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Common Misreadings", block)


def add_escalate_when(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Escalate When",
            "",
            "These conditions mean the problem is larger than a local wording fix and needs a wider review conversation.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Update This Page When", block)


def add_tradeoffs(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Tradeoffs To Hold",
            "",
            "A strong page names the tensions it is managing instead of pretending every desirable goal improves together.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Cross Implications", block)


def add_approval_questions(body: str, bullets: tuple[str, ...]) -> str:
    block = "\n".join(
        [
            "## Approval Questions",
            "",
            "A reviewer should be able to answer these clearly before trusting the page or the change it is helping to explain.",
            "",
            bullet_lines(bullets),
        ]
    )
    return insert_before_heading(body, "Evidence Checklist", block)


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
            "`bijux-canon` is a deliberately split retrieval-and-reasoning workspace.",
            "The repository does not hide everything behind one oversized package. It",
            "keeps ingest, index, reason, agent, and runtime as separate publishable",
            "packages so each boundary stays reviewable, testable, and explainable.",
            "",
            "This site is meant to be self-sufficient. A reader should be able to skim",
            "the root pages, understand why the split exists, and know where to go next",
            "without needing a meeting first.",
            "",
            '<div class="bijux-callout"><strong>Start with the package split, not the file tree.</strong> ',
            "Ingest prepares deterministic inputs. Index executes retrieval. Reason turns",
            "evidence into claims. Agent orchestrates role-based workflows. Runtime holds",
            "execution, replay, and acceptance authority. The root docs explain how those",
            "parts fit together without blurring their ownership.</div>",
            "",
            '<div class="bijux-panel-grid">',
            '  <div class="bijux-panel"><h3>What This Site Explains</h3><p>Why the repository is split, what each package owns, where shared schemas and rules live, and how maintainers prove that the split still holds.</p></div>',
            '  <div class="bijux-panel"><h3>What This Site Does Not Pretend</h3><p>It does not claim the docs are the source of truth by themselves. Every page is expected to point back to concrete code, schemas, tests, and release assets.</p></div>',
            '  <div class="bijux-panel"><h3>How To Read It Fast</h3><p>Use the repository handbook for cross-package questions, a product handbook for owned behavior, the maintainer handbook for repository automation, and the compatibility handbook for old names.</p></div>',
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
            "- start with [bijux-canon](bijux-canon/index.md) when the question crosses package boundaries or touches shared governance",
            "- open one product package when you need to know who owns behavior, interfaces, operations, or proof",
            "- use [bijux-canon-dev](bijux-canon-dev/index.md) for repository automation, schema enforcement, and maintainer-only guardrails" if "dev" in targets else "- maintainer automation pages are added when the dev section is rendered",
            "- use [compatibility packages](compat-packages/index.md) when you encounter an old distribution or import name and need the canonical replacement" if "compat" in targets else "- compatibility guidance is added when the compat section is rendered",
            "",
            "## Purpose",
            "",
            "This page is the front door to the handbook. Its job is to explain the shape of the system quickly enough that readers can choose the right branch before they drown in detail.",
            "",
            "## Stability",
            "",
            "This page is part of the canonical docs spine. Keep it aligned with the sections actually rendered in `docs/`, the packages that still ship from this repository, and the reasons the split exists.",
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
        "Treat the root page as the shortest honest explanation of the whole documentation system. It should help a reader understand the package split, the handbook layout, and the right next page before they commit to a longer read.",
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
        "Use this page to decide which handbook branch owns the current question. If a reader still cannot tell whether the issue is repository-wide, package-local, maintainer-only, or legacy-only after reading this page, then the root story is not clear enough yet.",
    )
    body = add_what_good_looks_like(
        body,
        (
            "the correct next handbook path becomes obvious within a few seconds",
            "the root page reduces orientation cost instead of adding another layer of ambiguity",
            "the documentation system feels intentionally divided rather than accidentally scattered",
        ),
    )
    body = add_failure_signals(
        body,
        (
            "the root page starts sounding like a summary of everything instead of a route to somewhere specific",
            "readers still need trial-and-error to find the right handbook branch",
            "the distinction between repository, package, maintainer, and compatibility docs becomes blurry again",
        ),
    )
    body = add_cross_implications(
        body,
        (
            "when this page drifts, every handbook branch becomes harder to discover correctly",
            "root routing mistakes amplify the cost of weak package or maintainer pages because readers reach them later",
            "the value of the whole docs system depends on this page remaining a fast orientation surface",
        ),
    )
    body = add_tradeoffs(
        body,
        (
            "prefer routing clarity over turning the root page into a compressed summary of every section",
            "prefer a small amount of duplication in navigation language over forcing readers to infer where a question belongs",
            "prefer stable handbook boundaries over a root index that changes shape every time one package adds material",
        ),
    )
    body = add_approval_questions(
        body,
        (
            "does the page still route most readers to one clearly better next section",
            "would a new reviewer understand the difference between repository, product, maintainer, and compatibility docs from this page alone",
            "is the navigation claim backed by the current rendered handbook structure rather than by intention only",
        ),
    )
    body = add_evidence_checklist(
        body,
        (
            "check `mkdocs.yml` against the rendered root navigation",
            "inspect `scripts/render_docs_catalog.py` if the page routing no longer reflects the intended handbook structure",
            "sample at least one target handbook branch to confirm the route this page recommends is still the right one",
        ),
    )
    body = add_antipatterns(
        body,
        (
            "turning the root page into a second copy of the whole handbook",
            "assuming navigation clarity emerges automatically from file count or section count",
            "treating handbook routing as cosmetic instead of as part of review efficiency",
        ),
    )
    body = add_escalate_when(
        body,
        (
            "the root page no longer routes readers to one clearly better next section",
            "major documentation branches overlap so much that readers cannot tell where a question belongs",
            "a structural handbook change would affect more than one section at once",
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
        "If this page is vague, readers start with the wrong mental model. They confuse package boundaries, over-ascribe responsibility to the root, and lose trust in the documentation before they ever reach the detailed pages.",
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

            The repository handbook explains the shared story above the package level:
            why this repository is split, which rules genuinely live at the root, and
            how the packages stay coordinated without collapsing back into one blurry
            codebase.

            `bijux-canon` is easiest to understand if you start from intent instead of
            from filenames. The repository exists to keep several deterministic,
            reviewable surfaces moving together: ingest prepares evidence, index makes
            retrieval executable, reason makes claims inspectable, agent turns role-based
            work into orchestrated runs, and runtime decides what execution and replay
            results are acceptable.

            <div class="bijux-callout"><strong>The root is a coordination layer, not a shadow owner.</strong>
            Product behavior should stay inside the publishable packages under `packages/`.
            The root only owns what is genuinely shared: workspace layout, schema
            governance, documentation rules, validation posture, and release
            coordination.</div>

            ## Pages in This Section

            {root_page_links}

            ## Shared Package Map

            {package_links}

            ## Purpose

            This page gives the shortest credible explanation of why the monorepo exists and what kind of questions belong in the repository handbook instead of a package handbook.

            ## Stability

            This page is part of the canonical docs spine. Keep it aligned with the current repository layout and the actual package set declared in `pyproject.toml`.
            """
        ),
        "platform-overview": textwrap.dedent(
            """\
            # Platform Overview

            `bijux-canon` is a multi-package system because the work is easier to reason
            about when preparation, retrieval, reasoning, orchestration, and runtime
            governance stay distinct. The split is not cosmetic. It is the main mechanism
            that keeps ownership explicit and review conversations short.

            Read the platform as a pipeline of responsibilities rather than a stack of
            directories. Ingest prepares deterministic material. Index turns retrieval
            behavior into an executable contract. Reason shapes evidence-backed claims.
            Agent coordinates role-local behavior and traceable runs. Runtime owns
            execution, replay, and acceptance authority across the wider flow.

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

            The repository root is intentionally narrow. It exists to coordinate packages
            that must move together, not to become a second implementation layer above
            them.

            A good scope test is simple: if a question can be answered honestly from one
            package handbook, it probably does not belong at the root. Root scope should
            stay reserved for rules, assets, and workflows that genuinely sit across
            package boundaries.

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
            concern belongs before they open any code. The directory tree is part of the
            design language: it should reinforce the package split instead of making it
            harder to see.

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

            The package map is the clearest explanation of the product idea in this
            repository. Each canonical package owns a distinct part of one larger system,
            and the split is the point:

            - `bijux-canon-ingest` prepares deterministic material from upstream inputs
            - `bijux-canon-index` executes retrieval and backend-facing vector behavior
            - `bijux-canon-reason` turns evidence into inspectable reasoning outcomes
            - `bijux-canon-agent` orchestrates role-based workflows and trace-backed runs
            - `bijux-canon-runtime` governs execution, replay, and acceptance authority

            The canonical packages each own a distinct slice of the overall system:

            {package_links}

            ## Shared Maintainer Packages

            - [bijux-canon-dev](../bijux-canon-dev/index.md) for repository automation, schema drift checks, SBOM support, and quality gates
            - [compatibility packages](../compat-packages/index.md) for legacy distribution and import preservation

            ## Purpose

            This page lets a reader see the whole system shape from one place before diving into package-local detail.

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

            That matters because the repository wants public surfaces to be reviewable in
            the open. A caller or reviewer should not need to reverse-engineer Python
            modules just to understand whether an HTTP or artifact contract changed.

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
            orchestration commands that keep the repository consistent. The goal is not to
            make every task happen at the root; it is to make cross-package work visible
            when it truly becomes cross-package.

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

            This distinction is essential for credibility. The repository should never ask
            readers to trust prose alone. If a rule matters, some checked-in package test,
            drift check, or CI workflow should be able to notice when it stops being true.

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

            The wording of the commit history matters here because the repository is meant
            to stay understandable years later. A good commit message should explain
            durable intent, not just what happened to be touched in one diff.

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

            The goal is not just consistency. The goal is reader trust. The handbook
            should let a new reviewer understand the design quickly, let a maintainer find
            concrete anchors without guesswork, and stay honest about what the docs can
            explain versus what only code and tests can prove.

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
        "These repository pages should explain the cross-package frame that no single package can explain alone. They are strongest when they make the monorepo easier to understand without turning the root into a second owner of package behavior.",
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
        f"Use `{title}` to decide whether the current question is genuinely repository-wide or whether it belongs back in one package handbook. If the answer depends mostly on one package's local behavior, this page should redirect instead of absorbing detail that the package should own.",
    )
    body = add_what_good_looks_like(
        body,
        (
            f"`{title}` keeps repository guidance above package-local detail instead of competing with it",
            "the reader can tell which root assets matter to the topic before opening code",
            "cross-package reasoning becomes simpler because the repository frame is explicit",
        ),
    )
    body = add_failure_signals(
        body,
        (
            f"`{title}` begins absorbing details that should live in package-local docs",
            "the page stops naming concrete root assets that support its claims",
            "reviewers cannot tell whether the page is describing policy, process, or one local implementation",
        ),
    )
    body = add_cross_implications(
        body,
        (
            "weak repository pages force package docs to carry root context they should not own",
            "schema, release, and automation review all become more fragmented when root guidance drifts",
            "maintainer pages become harder to interpret if repository policy is not clear first",
        ),
    )
    body = add_tradeoffs(
        body,
        (
            "prefer repository-wide clarity over squeezing package-specific nuance into root pages",
            "prefer durable repository rules over explanations that only fit the current implementation snapshot",
            "prefer explicit ownership boundaries between root, product, maintainer, and compatibility docs over a superficially shorter navigation tree",
        ),
    )
    body = add_approval_questions(
        body,
        (
            "does the page stay genuinely repository-wide instead of absorbing package-local detail",
            "can a reviewer tie the page's claims back to concrete root assets, workflows, or schemas",
            "would a package owner still agree that the root page is clarifying shared policy rather than redefining local ownership",
        ),
    )
    body = add_evidence_checklist(
        body,
        (
            "inspect the named root files, workflows, or schema directories directly",
            "check at least one owning package doc to confirm the repository page is not absorbing local detail",
            "verify that the page's policy language still has a checked-in enforcement or review mechanism behind it",
        ),
    )
    body = add_antipatterns(
        body,
        (
            "using repository pages to hide unresolved package-boundary decisions",
            "documenting root policy without naming the actual checked-in assets that support it",
            "letting one successful workflow example stand in for repository-wide truth",
        ),
    )
    body = add_escalate_when(
        body,
        (
            "a supposedly root decision is really moving package ownership around",
            "the page cannot stay accurate without changing multiple package handbooks too",
            "the root rule described here no longer has a clear checked-in enforcement path",
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
        "Repository pages matter because they explain the rules of coordination. Without them, every package has to re-explain shared schemas, release posture, and workspace expectations in slightly different words, and trust erodes fast.",
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
        "A cross-package change touches schemas, automation, and release behavior at once. The repository page should help the reviewer separate root-owned coordination from package-owned behavior instead of merging everything into one fuzzy story.",
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
        "These pages explain repository-level intent and shared rules, but they do not override package-local ownership. They also do not count as proof by themselves; the real backstops are the referenced files, workflows, schemas, and checks.",
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

            `bijux-canon-dev` is the maintainer package for repository health. It exists
            so schema drift checks, quality gates, supply-chain helpers, and release
            support have one clear home outside the end-user product surface.

            This package matters because hidden maintenance logic erodes trust fast. If
            contributors can only discover repository policy by reading CI output or shell
            glue, the monorepo stops feeling reviewable.

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

            `bijux-canon-dev` is intentionally not part of the end-user runtime. It is
            the package that keeps the monorepo honest when schemas drift, security
            tooling falls behind, or release metadata becomes inconsistent.

            A good maintainer package should reduce mystery, not create a new layer of
            it. This page should help readers see why the automation exists and why it
            does not belong in the product packages themselves.

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

            Its value depends on discipline. If maintainer code starts absorbing
            product behavior, the repository loses one of its most important
            boundaries: the difference between health tooling and product surface.

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

            Read this page as a map of repository-health responsibilities. It should let
            a contributor find the right maintenance code path without guessing whether
            the behavior is about quality, security, schema governance, release work, or
            supply-chain support.

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

            This page should make the gates feel concrete and inspectable. A quality bar
            is more credible when a contributor can point to the helper, the test, and
            the workflow that back it.

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

            This page is here to keep security work from becoming vague compliance
            theater. The useful question is always which checked-in tool or test is
            carrying the actual security expectation.

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

            Schema drift is one of the easiest ways to lose user trust quietly. This
            page should make it obvious where the repository checks that risk and why
            that work belongs in maintainer tooling.

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

            This page should help readers see release support as a coordination problem,
            not as hidden magic. If release logic matters, it should be visible, named,
            and tied to the workflows that actually use it.

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

            The point is not just compliance. The point is to keep dependency and build
            provenance explainable at repository level without smearing that burden
            across every product package.

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

            That is why this section needs to be unusually honest. A small maintainer
            change can carry wide consequences, so the package should bias toward
            explicit scope, explicit tests, and explicit explanations.

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
        ("explain automation", "see repository-health scope", "review package impact"),
        (
            ("Maintainer role", ("quality gates", "security gates")),
            ("Repository health", ("schema integrity", "supply-chain visibility")),
            ("Operational outcome", ("release clarity", "package consistency")),
        ),
    )
    body = add_working_interpretation(
        body,
        "These maintainer pages should read like explicit operational memory for repository-health work. They are strongest when they expose automation intent, package impact, and repository policy without pretending that CI logs are documentation.",
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
    body = add_failure_signals(
        body,
        (
            f"`{title}` starts reading like product documentation instead of maintainer guidance",
            "contributors can only discover maintainer behavior by reading scripts or CI output directly",
            "the page stops making package impact explicit when automation changes",
        ),
    )
    body = add_cross_implications(
        body,
        (
            "maintainer ambiguity leaks quickly into product package docs and repository workflows",
            "release and validation pressure becomes harder to reason about across the monorepo",
            "root governance pages become less actionable when maintainer intent is implicit",
        ),
    )
    body = add_tradeoffs(
        body,
        (
            "prefer repository-health clarity over convenience that only helps one maintainer's local workflow",
            "prefer checked-in automation expectations over undocumented operator heroics",
            "prefer explicit maintainer scope over letting dev pages quietly absorb product-contract decisions",
        ),
    )
    body = add_approval_questions(
        body,
        (
            "does the page still describe maintainer scope rather than end-user runtime behavior",
            "can contributors inspect the named automation, tests, or helpers that support the page",
            "is the product-package impact explicit enough that maintainers are not making contract changes by accident",
        ),
    )
    body = add_evidence_checklist(
        body,
        (
            "inspect the named helper modules under `packages/bijux-canon-dev/src/bijux_canon_dev`",
            "check the corresponding maintainer tests before trusting the page's operational claims",
            "confirm which product packages are affected so maintainer scope stays explicit",
        ),
    )
    body = add_antipatterns(
        body,
        (
            "describing maintainer automation as if it were part of the end-user runtime",
            "letting CI behavior become the only place where maintainer intent is visible",
            "changing repository-health tools without updating the maintainer story they imply",
        ),
    )
    body = add_escalate_when(
        body,
        (
            "a maintainer-only change starts affecting product package contracts directly",
            "the page can no longer describe scope without referencing multiple package ownership changes",
            "repository-health automation now requires a wider root policy decision",
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
        "Maintainer pages matter because hidden automation is one of the fastest ways for a monorepo to become hard to trust, hard to change, and hard to release safely. If the tooling is powerful but unexplained, contributors start treating the repository like a trap.",
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
        "This section can describe maintainer automation and repository health work, but it should never imply that maintainer tooling is part of the end-user product surface. It also should not pretend that hidden scripts count as documentation just because CI happens to run them.",
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

            They should be easy to understand but hard to romanticize. Their job is to
            reduce migration pain, not to compete with the canonical package family for
            new work.

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

            This page should help readers see the compatibility layer as a bridge with a
            cost. Preserving old names is sometimes necessary, but it is still a debt
            that should be visible and justified.

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

            This page should make the path forward feel more concrete than the comfort of
            staying on the legacy name. If readers leave unsure which name to use next,
            the migration story is still too weak.

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

            Thinness is the design goal here. These packages should preserve a path, not
            become a parallel product line with its own growing surface area.

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

            This page should make that temporary intent impossible to miss. Preserved
            imports are a migration aid, not a sign that the legacy name regained first-
            class status.

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

            This page should keep those commands in context. A preserved command should
            feel like a safety rail on the way to the canonical package, not like a new
            invitation to stay on the old name forever.

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

            A compatibility release should feel justified, narrow, and temporary. If the
            release story starts sounding like ordinary feature delivery, the layer is
            drifting away from its purpose.

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

            Small does not mean unimportant. These packages carry trust mainly through
            naming continuity, so the validation has to prove that the bridge still
            points to the right place.

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

            Retirement is where honesty matters most. A package should not survive on
            vague anxiety, and it should not disappear on untested optimism.

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
        ("map old names", "choose migration", "judge retirement"),
        (
            ("Legacy surface", ("distribution names", "import names")),
            ("Canonical target", ("current packages", "new work")),
            ("Decision pressure", ("migration pressure", "retirement readiness")),
        ),
    )
    body = add_working_interpretation(
        body,
        "These compatibility pages should make legacy names understandable without romanticizing them. Their value is in helping readers migrate with less ambiguity, not in making the old names feel equally current.",
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
    body = add_failure_signals(
        body,
        (
            f"`{title}` spends more time defending legacy names than clarifying migration",
            "the canonical target is harder to find than the old name",
            "retirement conversations keep stalling because the remaining need is not described concretely",
        ),
    )
    body = add_cross_implications(
        body,
        (
            "unclear compatibility pages slow adoption of the canonical package docs",
            "retirement planning becomes harder because repository and package owners lack one shared migration story",
            "legacy naming pressure can distort product package expectations if it is not kept explicitly separate",
        ),
    )
    body = add_tradeoffs(
        body,
        (
            "prefer a clear migration path over preserving every historical detail equally",
            "prefer honest legacy labeling over making old surfaces look more current than they are",
            "prefer repository-wide contract clarity over retaining compatibility language that now conflicts with canonical package docs",
        ),
    )
    body = add_approval_questions(
        body,
        (
            "does the page make the canonical replacement clearer than the legacy name itself",
            "is there still real evidence for preservation or is the section only reflecting habit",
            "would a reader leave knowing whether to migrate, preserve temporarily, or retire the legacy surface",
        ),
    )
    body = add_evidence_checklist(
        body,
        (
            "inspect the relevant `packages/compat-*` metadata and README files",
            "check the canonical target package docs named by this page",
            "confirm there is still a real migration consumer before accepting preservation as necessary",
        ),
    )
    body = add_antipatterns(
        body,
        (
            "treating compatibility shims like long-term product expansion points",
            "preserving legacy names because they are familiar rather than because they are needed",
            "letting migration guidance become less visible than the legacy label itself",
        ),
    )
    body = add_escalate_when(
        body,
        (
            "a legacy surface is still present but no one can name a real dependent consumer",
            "migration guidance now conflicts with the canonical package story",
            "retirement or preservation would affect more than one repository stakeholder group",
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
        "Compatibility pages matter because legacy package names often survive longer than the people who remember why they exist. Without explicit migration guidance, old names become sticky and retirement decisions become emotionally expensive instead of evidence-based.",
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
        "This section documents preserved legacy surfaces, but it does not claim those legacy names are the preferred place for new work or long-term design growth. If a legacy name remains, that is a migration fact, not a design endorsement.",
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
        "foundation": (
            f"Start the {package.title} handbook here when you need the package in one"
            " honest sentence: what it owns, why it exists, and where its boundary stops."
        ),
        "architecture": (
            f"Use the architecture section to understand how `{package.import_name}` is"
            " put together before you judge a refactor, a dependency change, or a new seam."
        ),
        "interfaces": (
            f"Use the interfaces section to see what `{package.title}` is really asking"
            " callers and operators to depend on, and which surfaces are stable enough to"
            " treat like contracts."
        ),
        "operations": (
            f"Use the operations section when you need to run, diagnose, release, or"
            f" support `{package.title}` without reconstructing the workflow from source."
        ),
        "quality": (
            f"Use the quality section to understand how `{package.title}` earns trust:"
            " which tests matter, which risks remain visible, and what done should mean"
            " after a real change."
        ),
    }
    return summaries[category]


def package_section_orientation(category: str, package: PackageInfo) -> str:
    orientations = {
        "foundation": (
            f"These pages establish the durable idea of `{package.title}`. A reader should"
            " be able to skim this section and understand why the package exists, what"
            " neighboring packages should not assume about it, and which claims are worth"
            " defending during review."
        ),
        "architecture": (
            f"These pages turn `{package.title}` from a directory tree into a readable"
            " design. They should help a reviewer trace responsibilities, execution paths,"
            " and pressure points quickly enough to keep structural conversations grounded."
        ),
        "interfaces": (
            f"These pages explain the public face of `{package.title}`. They exist so a"
            " caller can tell which commands, APIs, imports, schemas, and artifacts are"
            " deliberate surfaces rather than incidental visibility."
        ),
        "operations": (
            f"These pages are the checked-in operating memory for `{package.title}`. They"
            " should let a maintainer move from setup to diagnosis to release without"
            " depending on private habits or half-remembered shell history."
        ),
        "quality": (
            f"These pages explain the proof story for `{package.title}`. They should make"
            " it clear why the package is trustworthy today, what still needs explicit"
            " skepticism, and which review questions protect against shallow acceptance."
        ),
    }
    return orientations[category]


def related_links(package: PackageInfo, category: str, active_categories: tuple[str, ...]) -> str:
    reasons = {
        "foundation": "when you need the package boundary and ownership story",
        "architecture": "when the question becomes structural or execution-oriented",
        "interfaces": "when the question becomes caller-facing or contract-facing",
        "operations": "when the question becomes procedural, environmental, or release-oriented",
        "quality": "when the question becomes proof, risk, or review sufficiency",
    }
    section_links = []
    for other in active_categories:
        if other == category:
            continue
        section_links.append(f"- [{other.title()}](../{other}/index.md) {reasons[other]}")
    return "\n".join(section_links)


def package_map_destinations(category: str) -> tuple[str, ...]:
    destination_map = {
        "foundation": ("own the right work", "name the boundary", "compare neighbors"),
        "architecture": ("trace execution", "spot dependency pressure", "judge structural drift"),
        "interfaces": ("identify contracts", "see caller impact", "review compatibility"),
        "operations": ("repeat workflows", "find diagnostics", "release safely"),
        "quality": ("see proof", "see limitations", "judge done-ness"),
    }
    return destination_map[category]


def package_map_focus_sections(
    package: PackageInfo, category: str, title: str
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    focus_map = {
        "foundation": (
            ("Owned here", (package.owns[0], package.owns[1] if len(package.owns) > 1 else package.owns[0])),
            ("Not owned here", (package.not_owns[0], package.not_owns[1] if len(package.not_owns) > 1 else package.not_owns[0])),
            ("Proof anchors", (package.package_dir, f"{package.package_dir}/tests")),
        ),
        "architecture": (
            ("Module groups", (package.modules[0][1], package.modules[1][1] if len(package.modules) > 1 else package.modules[0][1])),
            ("Read in code", (package.modules[0][0], package.modules[1][0] if len(package.modules) > 1 else package.modules[0][0])),
            ("Design pressure", (title, package.tests[0])),
        ),
        "interfaces": (
            ("Caller surfaces", (package.interfaces[0], package.interfaces[1] if len(package.interfaces) > 1 else package.interfaces[0])),
            ("Contract evidence", (package.api_specs[0] if package.api_specs else package.release_notes[0], package.artifacts[0])),
            ("Review pressure", (title, package.tests[0])),
        ),
        "operations": (
            ("Workflow anchors", (package.package_dir + "/pyproject.toml", package.interfaces[0])),
            ("Operational evidence", (package.tests[0], package.artifacts[0])),
            ("Release pressure", (package.release_notes[0], title)),
        ),
        "quality": (
            ("Proof surfaces", (package.tests[0], package.tests[1] if len(package.tests) > 1 else package.tests[0])),
            ("Risk anchors", (package.release_notes[0], package.artifacts[0])),
            ("Review bar", (title, "package trust after change")),
        ),
    }
    return focus_map[category]


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

            {package_section_orientation(category, package)}

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
        package_map_destinations(category),
        package_map_focus_sections(package, category, title),
    )
    body = add_working_interpretation(body, package_working_interpretation(package, category))
    body = add_reader_fit_section(body, package_page_reader_fit(package, category))
    body = add_decision_rule(body, package_decision_rule(package, category, title))
    body = add_what_good_looks_like(body, package_what_good_looks_like(package, category, title))
    body = add_failure_signals(body, package_failure_signals(package, category, title))
    body = add_cross_implications(body, package_cross_implications(package, category))
    body = add_tradeoffs(body, package_tradeoffs(package, category))
    body = add_approval_questions(body, package_approval_questions(package, category, title))
    body = add_evidence_checklist(body, package_evidence_checklist(package, category))
    body = add_antipatterns(body, package_antipatterns(package, category))
    body = add_escalate_when(body, package_escalate_when(package, category))
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

`{package.title}` exists so one durable part of the system can stay legible.
Its job is to own {package.description.lower()}

If a reader cannot explain this package in one or two sentences after skimming
this page, the package boundary is still too fuzzy and later pages will inherit
that confusion.

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

This page names the line that keeps `{package.title}` useful instead of bloated.
The point of a package boundary is not to make work harder. It is to keep
neighboring packages from silently accumulating overlapping authority.

The non-goals matter as much as the goals. A package becomes easier to trust
when readers can see what it refuses to absorb just because the code happens to
be nearby.

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

Ownership in `{package.title}` should be visible in checked-in structure, not
only in prose. The source tree shows where the package expects work to live, and
the tests show whether that expectation is protected when the code changes.

Use this page when a change proposal feels plausible in more than one package
and someone needs a concrete reason to keep the work here or move it elsewhere.

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

`{package.title}` is one publishable part of a larger system. It sits in the
monorepo with its own `src/`, tests, metadata, and release history because the
repository wants package ownership to stay visible even when the packages evolve
together.

This page is here to answer a simple but important question: why is this work a
package at all, instead of just another folder inside a single giant project?

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

The fastest way to understand `{package.title}` is to map capabilities to the
code that carries them. This page should help a reader move from a package claim
to a likely code area without pretending that module names alone are enough.

When this page is healthy, the package feels like a set of deliberate abilities,
not a pile of implementation details.

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

The language around `{package.title}` should reinforce the real package
boundary. Good names shorten review. Weak names force people to keep asking
whether they are looking at local behavior or at something owned elsewhere.

This page keeps the package vocabulary stable enough that docs, code, commit
messages, and review conversations can describe the same idea without drift.

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
application code coordinate the work, and durable artifacts or responses leave
the package.

The value of this page is speed. A reader should be able to skim it and leave
with one coherent story about how work moves through `{package.title}` from
entrypoint to result.

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

Dependencies and adjacencies explain what `{package.title}` can do by itself and
what it deliberately leans on. They are part of the package story, not just
implementation trivia, because they show where local authority ends.

This page should help a reviewer see both kinds of dependency pressure: library
dependencies that shape the implementation, and neighboring packages that shape
the system boundary.

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

Changes in `{package.title}` should leave the package easier to explain, not
harder. A good change makes ownership clearer, contract language more honest,
and the proof story easier to follow.

These principles are not slogans. They are the filter for deciding whether a
local improvement is worth the long-term cost it creates for the rest of the
system.

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

The architecture of `{package.title}` becomes readable when its major module
groups are treated as responsibilities instead of as folders. This page should
help a reviewer move from a question about behavior to the part of the package
most likely to answer it.

When this page is useful, code reading becomes targeted rather than exploratory.

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

This is not only an aesthetic preference. Clear dependency direction keeps
refactors cheaper because reviewers can still tell which layers are allowed to
know about which other layers.

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
and workflows in application code, and delegating specific responsibilities to
owned modules.

This page should give a reader one clean story about how work moves through the
package. The goal is not to describe every branch, but to make the main path
recognizable before someone opens the implementation.

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

That clarity matters because state tends to spread silently when it is not named.
Once readers stop knowing which outputs are durable and which values are local,
interface and operations pages quickly become less trustworthy.

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

This page exists so integration changes do not feel mysterious. A reviewer should
be able to say which seams are intentional, which ones carry compatibility risk,
and where the package expects outside systems to meet it.

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

Good error explanations reduce two kinds of waste at once: operator confusion in
the moment and architectural confusion during later review. The package should
fail in ways that still preserve the boundary story.

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

This page is about where variation is welcomed and where it would be a design
smell. A package becomes easier to extend when contributors can see which seams
are meant to flex and which ones are carrying the core identity of the package.

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

This page is intentionally practical. Its purpose is to shorten the path from a
question in review to the files that actually explain the answer.

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

This page should keep risk language concrete. The right risks are the ones that
would make the package harder to reason about even if the current implementation
still appears to work.

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

The CLI surface is the operator-facing command layer for `{package.title}`. It
should tell a reader which commands are deliberate entrypoints and which ones
are just local implementation detail.

Command surfaces tend to become contracts early, because people script them,
share them in tickets, and paste them into automation. This page should make
that contract status visible instead of accidental.

## Command Facts

- canonical command: `{package.cli_command or "no package-level console script is declared"}`
- interface modules: {", ".join(package.interfaces)}

## Purpose

This page points maintainers toward the command entrypoints and their owning code.

## Stability

Keep it aligned with the declared scripts and the interface modules that implement them.
""",
            "api-surface": f"""# {title}

HTTP-facing behavior should be discoverable from tracked schema files and the
owning API modules.

The goal of this page is clarity before code-reading. A reviewer should be able
to see which API assets matter, where they live, and why a caller would treat
them as stable enough to depend on.

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

Configuration belongs at the package boundary, not scattered through unrelated
modules.

When configuration is documented well, maintainers can tell which behavior is
meant to vary without editing code. When it is documented poorly, package
behavior starts to feel magical or fragile.

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

This page keeps data shape changes reviewable. If a record or payload matters to
another package, another process, or a replay path, it deserves to be described
as a contract rather than left implicit in implementation details.

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

That means artifacts are not just outputs. They are promises about names,
layout, or semantics that downstream readers may already rely on. This page
should make those promises visible.

## Current Artifacts

{bullet_lines(package.artifacts)}

## Purpose

This page marks which outputs need stable review when behavior changes.

## Stability

Keep it aligned with the package outputs that are actually produced and consumed.
""",
            "entrypoints-and-examples": f"""# {title}

The fastest way to understand the package interfaces is to pair entrypoints
with concrete examples.

Examples are doing real work here. They let an impatient reader test whether the
package story is credible without reconstructing usage from source alone.

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

This page connects interface prose to real use. A reader should leave with a
picture of how commands, APIs, inputs, and outputs hang together in a workflow
an operator can actually repeat.

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

This page keeps import visibility honest. Not every importable symbol is public,
and not every public symbol should be left implicit. Readers should be able to
tell what the package is prepared to support as a Python-facing boundary.

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

This page should leave readers with a realistic sense of the compatibility bar.
It is more valuable to be clear about what triggers review than to sound
generously stable while leaving the real boundary ambiguous.

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

This page exists to keep setup honest. A maintainer should be able to tell which
files actually define installation truth and which dependencies are merely
present in the environment for unrelated reasons.

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

The point is not to prescribe one favorite workflow. It is to keep local work
close enough to the owning package that changes remain easy to explain and easy
to validate before they spread outward.

## Development Anchors

{bullet_lines(package.tests)}

## Purpose

This page records the package-local development posture.

## Stability

Keep it aligned with the actual test layout and maintenance workflow.
""",
            "common-workflows": f"""# {title}

Most work on `{package.title}` follows one of a few recurring paths.

This page should make those paths feel familiar and repeatable. Readers should
not have to rediscover the same workflow from scratch every time they debug,
extend, or review the package.

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

Good diagnostics shorten both incidents and reviews. They give maintainers a
way to connect visible outputs back to the package behavior that produced them.

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

This page keeps optimization work honest. A package is not healthier if it gets
faster by becoming harder to reason about, harder to replay, or easier to break
for downstream readers.

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

This page should help a maintainer stabilize the situation before they try to
improve it. The first question is not always how to fix the bug; it is how to
locate the right evidence quickly.

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

The release path is part of the product story because it determines how readers
learn what changed and what stayed stable. This page should make package-local
release mechanics understandable without separating them from repository rules.

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

This page keeps safety work concrete. A useful security discussion starts from
the actual interfaces, artifacts, and authority the package holds, not from
generic caution language detached from the codebase.

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

The point of this page is to protect the idea that packages are publishable
units. Even inside a monorepo, deployment assumptions should stay narrow enough
that the package can still be understood and operated as its own surface.

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

This page should help readers see the broad proof shape of the package rather
than treating the test tree like a bag of unrelated checks. A good strategy page
explains why these tests exist, not just where they live.

## Test Areas

{bullet_lines(package.tests)}

## Purpose

This page explains the broad testing shape of the package.

## Stability

Keep it aligned with the real test directories and the behaviors they protect.
""",
            "invariants": f"""# {title}

Invariants are the promises that should survive ordinary implementation change.

This page names the truths the package is trying hardest not to lose. If an
invariant changes, that should feel more like a design event than a routine code
edit.

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

The checklist is not here to slow people down with ceremony. It is here to stop
fast review from becoming shallow review when a change touches boundaries,
contracts, or proof.

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

Consistency matters here because readers should not need to relearn how to read
every package. The shared layout is part of the user experience, but honesty is
more important than uniformity for its own sake.

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

This page is where the package draws the line against false confidence. Done
should mean that behavior, explanation, and proof all move together.

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

This page should keep dependency review from feeling bureaucratic. Dependencies
matter because they reshape what the package relies on, what it exposes, and
what downstream maintainers must now trust.

## Current Dependency Themes

{bullet_lines(package.dependencies)}

## Purpose

This page explains why dependency review matters for the package.

## Stability

Keep it aligned with `pyproject.toml` and the package's real dependency posture.
""",
            "change-validation": f"""# {title}

Validation after a change should target the package surfaces that were actually touched.

This page is about choosing proof that matches the real risk. Strong validation
is not just more testing; it is testing and review aimed at the seam that moved.

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

This page protects credibility by keeping the current limits visible. Readers
should be able to tell what the package does not promise without mining issue
threads or learning the hard way in production.

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

This page should keep long-lived risk language attached to the package instead
of scattering it across reviews and memory. The goal is not alarmism; it is to
help maintainers remember which failures would actually cost credibility.

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
        "## Decision Rule",
        "## What Good Looks Like",
        "## Core Claim",
        "## Why It Matters",
        "## Failure Signals",
        "## If It Drifts",
        "## Representative Scenario",
        "## Tradeoffs To Hold",
        "## Cross Implications",
        "## Source Of Truth Order",
        "## Approval Questions",
        "## Evidence Checklist",
        "## Anti-Patterns",
        "## Common Misreadings",
        "## Concrete Anchors",
        "## Use This Page When",
        "## Next Checks",
        "## Escalate When",
        "## Update This Page When",
        "## What This Page Answers",
        "## Reviewer Lens",
        "## Honesty Boundary",
        "## Purpose",
        "## Stability",
    )
    narrative_headings = (
        "## What Good Looks Like",
        "## Failure Signals",
        "## Tradeoffs To Hold",
        "## Approval Questions",
        "## Evidence Checklist",
        "## Anti-Patterns",
        "## Escalate When",
    )
    failures: list[str] = []
    for path in sorted(DOCS_ROOT.rglob("*.md")):
        text = path.read_text(encoding="utf-8")
        if text.count("```mermaid") < 2:
            failures.append(f"{path}: fewer than two Mermaid diagrams")
        for heading in required_headings:
            if heading not in text:
                failures.append(f"{path}: missing heading {heading}")
        lines = text.splitlines()
        for heading in narrative_headings:
            try:
                index = lines.index(heading)
            except ValueError:
                continue
            probe = index + 1
            while probe < len(lines) and not lines[probe].strip():
                probe += 1
            if probe >= len(lines):
                failures.append(f"{path}: heading {heading} has no narrative lead-in")
                continue
            if lines[probe].startswith("- ") or lines[probe].startswith("## "):
                failures.append(f"{path}: heading {heading} is missing a narrative lead-in")
        if text.count("- ") < 45:
            failures.append(f"{path}: too few bullet points for current handbook depth standard")
        word_count = len(text.split())
        if word_count < 850:
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
