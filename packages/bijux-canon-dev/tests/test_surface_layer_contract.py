"""Repository contract for thin CLI and HTTP transport layers."""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CANONICAL_PACKAGES = (
    "bijux-canon-agent",
    "bijux-canon-index",
    "bijux-canon-ingest",
    "bijux-canon-reason",
    "bijux-canon-runtime",
)
FORBIDDEN_INFRASTRUCTURE = (".infra", ".observability.storage")
FORBIDDEN_CONTROLLER_LAYERS = (
    "domain",
    "evaluation",
    "execution",
    "pipeline",
    "reasoning",
    "retrieval",
    "tooling",
    "verification",
)
FORBIDDEN_CONSTRUCTORS = {
    "AuditableDocPipeline",
    "DuckDBExecutionReadStore",
    "DuckDBExecutionStore",
    "DuckDBExecutionWriteStore",
    "FileStorage",
    "RunBuilder",
}


def _surface_files() -> list[Path]:
    files: list[Path] = []
    for distribution in CANONICAL_PACKAGES:
        source_root = REPO_ROOT / "packages" / distribution / "src"
        files.extend(source_root.glob("*/api/v1/*.py"))
        files.extend(source_root.glob("*/interfaces/cli/*.py"))
    return sorted(files)


def _controller_file(path: Path) -> bool:
    if "/api/v1/" in path.as_posix():
        return True
    return path.name in {"app.py", "entrypoint.py", "main.py"} or path.name.endswith(
        "_commands.py"
    )


def _imports(tree: ast.AST) -> list[tuple[int, str]]:
    imports: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports.extend((node.lineno, alias.name) for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imports.append((node.lineno, node.module))
    return imports


def _call_name(node: ast.expr) -> str:
    if isinstance(node, ast.Name):
        return node.id
    if isinstance(node, ast.Attribute):
        return _call_name(node.value) + "." + node.attr
    return ""


def _forbidden_controller_import(module: str) -> bool:
    parts = module.split(".")
    if len(parts) < 2 or not parts[0].startswith("bijux_canon_"):
        return False
    if parts[1] in FORBIDDEN_CONTROLLER_LAYERS:
        return True
    return parts[1:3] == ["traces", "replay"]


def test_surfaces_do_not_import_concrete_infrastructure() -> None:
    violations: list[str] = []
    for path in _surface_files():
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, module in _imports(tree):
            if any(part in module for part in FORBIDDEN_INFRASTRUCTURE):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line}: {module}")
    assert not violations, "surface infrastructure imports:\n" + "\n".join(violations)


def test_transport_controllers_delegate_domain_behavior() -> None:
    violations: list[str] = []
    for path in (item for item in _surface_files() if _controller_file(item)):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for line, module in _imports(tree):
            if _forbidden_controller_import(module):
                violations.append(f"{path.relative_to(REPO_ROOT)}:{line}: {module}")
        for node in ast.walk(tree):
            if isinstance(node, ast.Call):
                constructor = _call_name(node.func).rsplit(".", maxsplit=1)[-1]
                if constructor in FORBIDDEN_CONSTRUCTORS:
                    violations.append(
                        f"{path.relative_to(REPO_ROOT)}:{node.lineno}: {constructor}()"
                    )
    assert not violations, "transport-owned domain behavior:\n" + "\n".join(violations)
