# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Select the minimum mandatory verification for a repository change set."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import dataclass
import fnmatch
from importlib.resources import files
import json
from pathlib import Path, PurePosixPath
import subprocess
from typing import cast


@dataclass(frozen=True, slots=True)
class SelectedCheck:
    """One mandatory check and the rules that selected it."""

    check_id: str
    command: tuple[str, ...]
    description: str
    rule_ids: tuple[str, ...]
    reasons: tuple[str, ...]

    def record(self) -> dict[str, object]:
        """Return the stable machine-readable representation."""
        return {
            "check_id": self.check_id,
            "command": list(self.command),
            "description": self.description,
            "reasons": list(self.reasons),
            "rule_ids": list(self.rule_ids),
        }


@dataclass(frozen=True, slots=True)
class ImpactSelection:
    """Deterministic checks and matched contract ownership for changed paths."""

    paths: tuple[str, ...]
    checks: tuple[SelectedCheck, ...]
    interfaces: tuple[str, ...]
    consumers: tuple[str, ...]
    generated_outputs: tuple[str, ...]
    matched_rule_ids: tuple[str, ...]
    schema_version: str = "bijux.canon.verification-impact-selection.v1"

    def record(self) -> dict[str, object]:
        """Return stable JSON suitable for CI and review evidence."""
        return {
            "checks": [check.record() for check in self.checks],
            "consumers": list(self.consumers),
            "generated_outputs": list(self.generated_outputs),
            "interfaces": list(self.interfaces),
            "matched_rule_ids": list(self.matched_rule_ids),
            "paths": list(self.paths),
            "schema_version": self.schema_version,
        }


def _load_map() -> dict[str, object]:
    resource = files("bijux_canon_dev.verification").joinpath("impact_map.json")
    value = json.loads(resource.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("verification impact map must be a JSON object")
    if value.get("schema_version") != "bijux.canon.verification-impact.v1":
        raise ValueError("verification impact map schema is unsupported")
    return cast(dict[str, object], value)


def _normalize_path(value: str) -> str:
    normalized = PurePosixPath(value.replace("\\", "/")).as_posix()
    while normalized.startswith("./"):
        normalized = normalized[2:]
    if normalized in {"", "."} or normalized == ".." or normalized.startswith("../"):
        raise ValueError(f"changed path must be repository-relative: {value}")
    return normalized


def _matches(path: str, patterns: Sequence[str]) -> bool:
    return any(fnmatch.fnmatchcase(path, pattern) for pattern in patterns)


def select_checks(
    changed_paths: Sequence[str],
    *,
    added_checks: Sequence[str] = (),
    impact_map: dict[str, object] | None = None,
) -> ImpactSelection:
    """Select mandatory checks; caller overrides may add but never remove checks."""
    mapping = _load_map() if impact_map is None else impact_map
    paths = tuple(sorted({_normalize_path(path) for path in changed_paths}))
    if not paths:
        raise ValueError("at least one changed path is required")
    checks = cast(dict[str, dict[str, object]], mapping.get("checks"))
    rules = cast(list[dict[str, object]], mapping.get("rules"))
    if not isinstance(checks, dict) or not isinstance(rules, list):
        raise ValueError("verification impact map checks and rules are required")

    selected_by: dict[str, list[tuple[str, str]]] = {}
    interfaces: set[str] = set()
    consumers: set[str] = set()
    matched_rule_ids: list[str] = []
    for rule in rules:
        rule_id = str(rule["id"])
        patterns = tuple(
            str(pattern) for pattern in cast(list[object], rule["patterns"])
        )
        if not any(_matches(path, patterns) for path in paths):
            continue
        matched_rule_ids.append(rule_id)
        reason = str(rule["reason"])
        interfaces.update(str(item) for item in cast(list[object], rule["interfaces"]))
        consumers.update(str(item) for item in cast(list[object], rule["consumers"]))
        for check_id in cast(list[str], rule["checks"]):
            selected_by.setdefault(check_id, []).append((rule_id, reason))

    for check_id in added_checks:
        if check_id not in checks:
            raise ValueError(f"unknown additive check: {check_id}")
        selected_by.setdefault(check_id, []).append(
            ("maintainer-override", "Maintainer requested additional verification.")
        )
    if not selected_by:
        selected_by["repository-configuration"] = [
            (
                "unmapped-path-fallback",
                "An owned repository path has no narrower mapping; validate repository configuration.",
            )
        ]
        matched_rule_ids.append("unmapped-path-fallback")

    selected: list[SelectedCheck] = []
    for check_id in sorted(selected_by):
        definition = checks.get(check_id)
        if not isinstance(definition, dict):
            raise ValueError(f"impact rule references unknown check: {check_id}")
        sources = selected_by[check_id]
        selected.append(
            SelectedCheck(
                check_id=check_id,
                command=tuple(
                    str(item) for item in cast(list[object], definition["command"])
                ),
                description=str(definition["description"]),
                rule_ids=tuple(rule_id for rule_id, _reason in sources),
                reasons=tuple(dict.fromkeys(reason for _rule_id, reason in sources)),
            )
        )
    return ImpactSelection(
        paths=paths,
        checks=tuple(selected),
        interfaces=tuple(sorted(interfaces)),
        consumers=tuple(sorted(consumers)),
        generated_outputs=tuple(
            str(item) for item in cast(list[object], mapping["generated_outputs"])
        ),
        matched_rule_ids=tuple(matched_rule_ids),
    )


def _git_paths(repository: Path, *, base: str | None, head: str) -> tuple[str, ...]:
    commands: list[list[str]]
    if base is not None:
        commands = [["git", "diff", "--name-only", "-z", f"{base}...{head}"]]
    else:
        commands = [
            ["git", "diff", "--name-only", "-z"],
            ["git", "diff", "--cached", "--name-only", "-z"],
            ["git", "ls-files", "--others", "--exclude-standard", "-z"],
        ]
    paths: set[str] = set()
    for command in commands:
        result = subprocess.run(
            command,
            cwd=repository,
            check=True,
            capture_output=True,
        )
        paths.update(
            item.decode("utf-8") for item in result.stdout.split(b"\0") if item
        )
    return tuple(sorted(paths))


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Select mandatory focused checks from changed repository paths.",
    )
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--path", action="append", default=[])
    parser.add_argument("--base")
    parser.add_argument("--head", default="HEAD")
    parser.add_argument("--add-check", action="append", default=[])
    parser.add_argument("--format", choices=("text", "json"), default="text")
    return parser


def _render_text(selection: ImpactSelection) -> str:
    lines = ["Changed paths:"]
    lines.extend(f"  - {path}" for path in selection.paths)
    lines.append("Required checks:")
    for check in selection.checks:
        lines.append(f"  - {check.check_id}: {' '.join(check.command)}")
        lines.extend(f"    reason: {reason}" for reason in check.reasons)
    if selection.interfaces:
        lines.append("Affected interfaces: " + "; ".join(selection.interfaces))
    if selection.consumers:
        lines.append("Transitive consumers: " + "; ".join(selection.consumers))
    if selection.generated_outputs:
        lines.append(
            "Governed generated outputs: " + "; ".join(selection.generated_outputs)
        )
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the contributor-facing impact selector."""
    args = _parser().parse_args(argv)
    paths = tuple(args.path) or _git_paths(
        args.repo.resolve(),
        base=args.base,
        head=args.head,
    )
    try:
        selection = select_checks(paths, added_checks=args.add_check)
    except ValueError as exc:
        raise SystemExit(str(exc)) from exc
    if args.format == "json":
        print(json.dumps(selection.record(), sort_keys=True, separators=(",", ":")))
    else:
        print(_render_text(selection))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
