"""Invariant: pipeline layering stays decoupled."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN = {
    "execution": ("bijux_agent.pipeline.results",),
    "results": ("bijux_agent.pipeline.execution",),
}


def _iter_package_files(root: Path, package: str) -> list[Path]:
    base = root / "src" / "bijux_agent" / "pipeline" / package
    return [path for path in base.rglob("*.py") if path.is_file()]


def _resolve_relative(module: str | None, level: int, package: str) -> str | None:
    if module is None:
        module = ""
    if level == 0:
        return module or None
    base_parts = ["bijux_agent", "pipeline", package]
    if level > len(base_parts):
        return None
    resolved = base_parts[:-level]
    if module:
        resolved.extend(module.split("."))
    return ".".join(resolved) if resolved else None


def _find_forbidden_imports(
    paths: list[Path], prefixes: tuple[str, ...], package: str
) -> list[str]:
    violations: list[str] = []
    for path in paths:
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.startswith(prefixes):
                        violations.append(f"{path}:{node.lineno} import {alias.name}")
                        return violations
            elif isinstance(node, ast.ImportFrom):
                resolved = _resolve_relative(node.module, node.level, package)
                if resolved and resolved.startswith(prefixes):
                    violations.append(f"{path}:{node.lineno} from {resolved}")
                    return violations
    return violations


def test_pipeline_layering() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    for package, prefixes in FORBIDDEN.items():
        violations = _find_forbidden_imports(
            _iter_package_files(repo_root, package), prefixes, package
        )
        assert not violations, "Pipeline layering violations found:\n" + "\n".join(
            violations
        )
