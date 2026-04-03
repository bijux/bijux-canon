from __future__ import annotations

import argparse
from pathlib import Path

from packaging.requirements import Requirement

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover
    import tomli as tomllib


def repo_root_for(pyproject_path: Path) -> Path:
    return pyproject_path.resolve().parents[2]


def local_package_map(pyproject_path: Path) -> dict[str, Path]:
    packages_dir = repo_root_for(pyproject_path) / "packages"
    package_map: dict[str, Path] = {}
    for candidate in packages_dir.glob("*/pyproject.toml"):
        project = tomllib.loads(candidate.read_text(encoding="utf-8")).get("project", {})
        name = project.get("name")
        if isinstance(name, str):
            package_map[name] = candidate.parent.resolve()
    return package_map


def render_local_requirement(requirement_text: str, package_map: dict[str, Path]) -> str:
    requirement = Requirement(requirement_text)
    package_dir = package_map.get(requirement.name)
    if package_dir is None or requirement.url is not None:
        return requirement_text

    extras = ""
    if requirement.extras:
        extras = "[" + ",".join(sorted(requirement.extras)) + "]"

    marker = ""
    if requirement.marker is not None:
        marker = f"; {requirement.marker}"

    return f"{requirement.name}{extras} @ {package_dir.as_uri()}{marker}"


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def load_project(pyproject_path: Path) -> dict[str, object]:
    data = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    return data.get("project", {})


def write_requirements(
    pyproject_path: Path,
    output_path: Path,
    group: str,
    optional_group: str,
) -> int:
    project = load_project(pyproject_path)
    dependencies = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    package_map = local_package_map(pyproject_path)

    if group == "dev":
        dependencies.extend(optional.get(optional_group, []))

    rendered = [render_local_requirement(dependency, package_map) for dependency in dependencies]
    payload = "\n".join(dedupe(rendered)).strip()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(f"{payload}\n" if payload else "", encoding="utf-8")
    return 0


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Write requirements.txt content for pip-audit.")
    parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    parser.add_argument("--output", required=True, help="Path to requirements output")
    parser.add_argument(
        "--group",
        choices=("prod", "dev"),
        required=True,
        help="Dependency group to export.",
    )
    parser.add_argument(
        "--optional-group",
        default="dev",
        help="Optional dependency group to append for the dev export.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    return write_requirements(
        pyproject_path=Path(args.pyproject),
        output_path=Path(args.output),
        group=args.group,
        optional_group=args.optional_group,
    )


if __name__ == "__main__":
    raise SystemExit(main())
