from __future__ import annotations

from pathlib import Path


MAX_LINES = 600
EXCLUDED_DIRS = {"artifacts", ".venv", "htmlcov", "build", "dist", "node_modules", ".tox"}
EXEMPT_PATHS = {
    "src/bijux_canon_agent/agents/critique/core.py",
    "src/bijux_canon_agent/agents/file_reader/agent.py",
    "src/bijux_canon_agent/agents/file_reader/capabilities/universal_file_reader_core.py",
    "tests/unit/test_pipeline_flow.py",
}


def package_root() -> Path:
    return Path(__file__).resolve().parents[6] / "packages" / "bijux-canon-agent"


def is_excluded(path: Path) -> bool:
    return any(part in EXCLUDED_DIRS for part in path.parts)


def main() -> int:
    root = package_root()
    offenders: list[tuple[Path, int]] = []
    for path in root.rglob("*.py"):
        if is_excluded(path) or path.name.startswith("."):
            continue
        relative = str(path.relative_to(root))
        if relative in EXEMPT_PATHS:
            continue
        line_count = sum(1 for _ in path.open("r", encoding="utf-8", errors="ignore"))
        if line_count > MAX_LINES:
            offenders.append((path, line_count))

    if offenders:
        print(f"error: the following Python files exceed the {MAX_LINES}-line limit:")
        for path, count in sorted(offenders):
            print(f" - {path.relative_to(root)} ({count} lines)")
        return 1

    print("line limit check passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
