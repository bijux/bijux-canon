"""Keep primary product documentation synchronized with installed surfaces."""

from __future__ import annotations

from pathlib import Path
import re
import tomllib

REPO_ROOT = Path(__file__).resolve().parents[3]
RUNTIME_DOCS = REPO_ROOT / "docs/06-bijux-canon-runtime"
PRIMARY_PRODUCT_PAGES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "packages/bijux-canon-runtime/README.md",
    RUNTIME_DOCS / "index.md",
    RUNTIME_DOCS / "interfaces/index.md",
    RUNTIME_DOCS / "interfaces/cli-surface.md",
    RUNTIME_DOCS / "interfaces/api-surface.md",
    RUNTIME_DOCS / "interfaces/entrypoints-and-examples.md",
    RUNTIME_DOCS / "interfaces/operator-workflows.md",
    RUNTIME_DOCS / "operations/index.md",
    RUNTIME_DOCS / "operations/installation-and-setup.md",
    RUNTIME_DOCS / "operations/common-workflows.md",
    RUNTIME_DOCS / "quality/known-limitations.md",
    REPO_ROOT / "examples/ancient-dna-research/README.md",
)
ROOT_API_PAGES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "docs/01-bijux-canon/index.md",
    REPO_ROOT / "docs/01-bijux-canon/foundation/repository-scope.md",
    REPO_ROOT / "docs/01-bijux-canon/operations/api-and-schema-governance.md",
    REPO_ROOT / "docs/07-bijux-canon-maintain/bijux-canon-dev/module-map.md",
    REPO_ROOT / "docs/07-bijux-canon-maintain/bijux-canon-dev/schema-governance.md",
)
NEW_USER_PAGES = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "packages/bijux-canon-runtime/README.md",
    RUNTIME_DOCS / "index.md",
    RUNTIME_DOCS / "interfaces/entrypoints-and-examples.md",
    RUNTIME_DOCS / "interfaces/operator-workflows.md",
    RUNTIME_DOCS / "operations/installation-and-setup.md",
    RUNTIME_DOCS / "operations/common-workflows.md",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_primary_pages_do_not_restore_obsolete_composition_claims() -> None:
    forbidden = (
        "no installed `bijux-canon-index` console script",
        "canonical lower-package root callables are currently missing",
        "runtime has no reason adapter",
        "runtime has no agent adapter",
        "the strongest immediately reproducible whole-repository demonstration",
        "the live step executors currently resolve four package-root callables",
        "the current ingest, index, reason, and agent roots do not expose",
    )
    failures: list[str] = []
    for path in PRIMARY_PRODUCT_PAGES:
        text = _read(path).lower()
        for claim in forbidden:
            if claim in text:
                failures.append(f"{path.relative_to(REPO_ROOT)}: {claim}")
    assert not failures, "obsolete product claims remain:\n" + "\n".join(failures)


def test_root_api_pages_identify_runtime_v2_as_the_primary_contract() -> None:
    combined = "\n".join(_read(path) for path in ROOT_API_PAGES)

    assert all("Runtime v2" in _read(path) for path in ROOT_API_PAGES)
    assert "apis/<package>/v1" not in combined
    assert "apis/<distribution>/v1" not in combined
    assert "five versioned HTTP contracts" not in combined
    assert "six versioned HTTP contracts" in combined


def test_new_user_pages_use_installed_v2_commands() -> None:
    legacy_command = re.compile(
        r"bijux-canon-runtime (?:plan|dry-run|run|unsafe-run|replay|inspect run|diff run)\b"
    )
    failures: list[str] = []
    for path in NEW_USER_PAGES:
        text = _read(path)
        if legacy_command.search(text):
            failures.append(f"{path.relative_to(REPO_ROOT)}: legacy manifest command")
        if "/api/v1/" in text or "api.v1.app:app" in text:
            failures.append(
                f"{path.relative_to(REPO_ROOT)}: v1 route or server command"
            )
    assert not failures, "primary workflow bypasses Runtime v2:\n" + "\n".join(failures)


def test_primary_workflows_cover_operational_lifecycle() -> None:
    combined = "\n".join(_read(path) for path in NEW_USER_PAGES)
    required = (
        "bijux-canon-runtime init",
        "bijux-canon-runtime v2 ready",
        "bijux-canon-runtime v2 run",
        "bijux-canon-runtime v2 result",
        "bijux-canon-runtime v2 inspect",
        "bijux-canon-runtime v2 replay",
        "bijux-canon-runtime v2 compare",
        "bijux-canon-runtime v2 cancel",
        "bijux-canon-runtime v2 backup",
        "bijux-canon-runtime v2 restore",
        "bijux-canon-runtime-server",
        "bijux-canon-index model acquire",
        "bijux-canon-index model validate",
    )
    assert all(command in combined for command in required)


def test_documented_v2_commands_are_declared_by_the_parser() -> None:
    parser_source = _read(
        REPO_ROOT
        / "packages/bijux-canon-runtime/src/bijux_canon_runtime/interfaces/cli/v2_parser.py"
    )
    declared = set(re.findall(r'commands\.add_parser\(\s*"([a-z-]+)"', parser_source))
    for names in re.findall(
        r"for name(?:, help_text)? in \((.*?)\):", parser_source, re.DOTALL
    ):
        declared.update(re.findall(r'"([a-z-]+)"', names))

    documented: set[str] = set()
    pattern = re.compile(r"bijux-canon-runtime v2 ([a-z-]+)")
    for path in PRIMARY_PRODUCT_PAGES:
        documented.update(pattern.findall(_read(path)))

    assert documented
    assert documented <= declared


def test_root_readme_names_every_canonical_installed_command() -> None:
    readme = _read(REPO_ROOT / "README.md")
    packages = (
        "bijux-canon-ingest",
        "bijux-canon-index",
        "bijux-canon-reason",
        "bijux-canon-agent",
        "bijux-canon-runtime",
    )
    for package in packages:
        with (REPO_ROOT / f"packages/{package}/pyproject.toml").open("rb") as handle:
            project = tomllib.load(handle)["project"]
        scripts = project["scripts"]
        assert package in scripts
        assert f"{package} --help" in readme

    runtime_readme = _read(REPO_ROOT / "packages/bijux-canon-runtime/README.md")
    assert "bijux-canon-runtime-server" in runtime_readme
