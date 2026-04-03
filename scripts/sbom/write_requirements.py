from __future__ import annotations

import argparse
import subprocess
import tomllib
from pathlib import Path
from packaging.requirements import Requirement


def repo_root_for(pyproject_path: Path) -> Path:
    return pyproject_path.resolve().parents[2]


def local_package_map(pyproject_path: Path) -> dict[str, Path]:
    packages_dir = repo_root_for(pyproject_path) / "packages"
    package_map: dict[str, Path] = {}

    for candidate in packages_dir.glob("*/pyproject.toml"):
        project = tomllib.loads(candidate.read_text()).get("project", {})
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


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write pip-audit requirements or resolve version from pyproject metadata."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    write_parser = subparsers.add_parser(
        "write-requirements",
        help="Write requirements.txt content for pip-audit.",
    )
    write_parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    write_parser.add_argument("--output", required=True, help="Path to requirements output")
    write_parser.add_argument(
        "--group",
        choices=("prod", "dev"),
        required=True,
        help="Dependency group to export.",
    )
    write_parser.add_argument(
        "--optional-group",
        default="dev",
        help="Optional dependency group to append for the dev export.",
    )

    version_parser = subparsers.add_parser(
        "resolve-version",
        help="Resolve a package version from pyproject metadata or package tags.",
    )
    version_parser.add_argument("--pyproject", required=True, help="Path to pyproject.toml")
    version_parser.add_argument("--package-name", required=True, help="Package slug/tag prefix")
    return parser.parse_args()


def dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    ordered: list[str] = []
    for item in items:
        if item not in seen:
            seen.add(item)
            ordered.append(item)
    return ordered


def load_project(pyproject_path: str) -> dict:
    pyproject = Path(pyproject_path)
    data = tomllib.loads(pyproject.read_text())
    return data.get("project", {})


def write_requirements(
    pyproject_path: str, output_path: str, group: str, optional_group: str
) -> int:
    pyproject = Path(pyproject_path)
    project = load_project(pyproject_path)
    dependencies = list(project.get("dependencies", []))
    optional = project.get("optional-dependencies", {})
    package_map = local_package_map(pyproject)

    if group == "dev":
        dependencies.extend(optional.get(optional_group, []))

    resolved_dependencies = [
        render_local_requirement(dependency, package_map) for dependency in dependencies
    ]

    output = Path(output_path)
    output.parent.mkdir(parents=True, exist_ok=True)
    payload = "\n".join(dedupe(resolved_dependencies)).strip()
    output.write_text(f"{payload}\n" if payload else "", encoding="utf-8")
    return 0


def resolve_version(pyproject_path: str, package_name: str) -> int:
    project = load_project(pyproject_path)
    version = project.get("version")
    if version:
        print(version)
        return 0

    tag = subprocess.run(
        ["git", "tag", "--sort=v:refname", "--list", f"{package_name}/v*"],
        capture_output=True,
        check=False,
        text=True,
    )
    tags = [line.strip() for line in tag.stdout.splitlines() if line.strip()]
    if tags:
        print(tags[-1].removeprefix(f"{package_name}/v"))
        return 0

    print("0.0.0")
    return 0


def main() -> int:
    args = parse_args()
    if args.command == "write-requirements":
        return write_requirements(args.pyproject, args.output, args.group, args.optional_group)
    return resolve_version(args.pyproject, args.package_name)


if __name__ == "__main__":
    raise SystemExit(main())
