"""Audit unfinished-work markers across advertised repository surfaces."""

from __future__ import annotations

import argparse
from collections import Counter
from collections.abc import Mapping, Sequence
from fnmatch import fnmatch
import json
from pathlib import Path
import re
import subprocess
from typing import Any, cast


class PlaceholderAuditError(RuntimeError):
    """The marker policy is incomplete, stale, or invalid."""


_MARKER = re.compile(
    r"\b(?:todo|fixme|tbd)\b|placeholder|notimplemented|not implemented",
    re.IGNORECASE,
)
_CLASSIFICATIONS = {
    "implemented_product_path",
    "valid_abstract_method_or_template",
    "explicit_experimental_or_deprecated_limitation",
    "removed_claim",
}
_ROOT_FILES = {"CHANGELOG.md", "README.md"}
_ROOT_PREFIXES = ("apis/", "docs/", "examples/", "packages/")


def _require(condition: object, message: str) -> None:
    if not condition:
        raise PlaceholderAuditError(message)


def _object(value: object, message: str) -> dict[str, Any]:
    _require(isinstance(value, dict), message)
    return cast(dict[str, Any], value)


def _strings(value: object, message: str) -> list[str]:
    _require(
        isinstance(value, list) and all(isinstance(item, str) for item in value),
        message,
    )
    return cast(list[str], value)


def _tracked_paths(repository: Path) -> tuple[str, ...]:
    completed = subprocess.run(
        ("git", "-C", str(repository), "ls-files", "-z"),
        capture_output=True,
        check=False,
    )
    _require(completed.returncode == 0, "cannot enumerate tracked repository files")
    return tuple(
        item.decode("utf-8")
        for item in completed.stdout.split(b"\0")
        if item
    )


def _marker_kind(text: str) -> str:
    lowered = text.lower()
    if "placeholder" in lowered:
        return "placeholder"
    if re.search(r"\b(todo|fixme|tbd)\b", lowered):
        return "deferred_work"
    return "not_implemented"


def _in_scope(
    path: str,
    *,
    excluded_exact: set[str],
    excluded_prefixes: tuple[str, ...],
) -> bool:
    if path in excluded_exact or path.startswith(excluded_prefixes):
        return False
    if "/tests/" in path or "/__pycache__/" in path:
        return False
    if path.startswith("examples/") and "/corpus/sources/" in path:
        return False
    return path in _ROOT_FILES or path.startswith(_ROOT_PREFIXES)


def scan_markers(repository: Path, policy: Mapping[str, Any]) -> list[dict[str, Any]]:
    """Return one record for every marker-bearing line in governed files."""
    excluded_exact = set(
        _strings(policy.get("excluded_exact_paths"), "excluded paths are invalid")
    )
    excluded_prefixes = tuple(
        _strings(policy.get("excluded_prefixes"), "excluded prefixes are invalid")
    )
    occurrences: list[dict[str, Any]] = []
    for relative in _tracked_paths(repository):
        if not _in_scope(
            relative,
            excluded_exact=excluded_exact,
            excluded_prefixes=excluded_prefixes,
        ):
            continue
        payload = (repository / relative).read_bytes()
        if b"\0" in payload:
            continue
        for line_number, line in enumerate(
            payload.decode("utf-8", errors="replace").splitlines(), start=1
        ):
            match = _MARKER.search(line)
            if match:
                occurrences.append(
                    {
                        "line": line_number,
                        "marker_kind": _marker_kind(match.group(0)),
                        "path": relative,
                    }
                )
    return occurrences


def audit_repository(repository: Path, policy_path: Path) -> dict[str, Any]:
    """Validate every marker against a reviewed, fail-closed policy rule."""
    repository = repository.resolve()
    policy = _object(json.loads(policy_path.read_text()), "policy must be an object")
    _require(
        policy.get("schema_version") == "bijux.canon.placeholder_audit_policy.v1",
        "placeholder audit policy schema mismatch",
    )
    raw_rules = policy.get("rules")
    _require(isinstance(raw_rules, list), "placeholder audit rules are missing")
    rules = [
        _object(item, "placeholder audit rule is invalid")
        for item in cast(list[object], raw_rules)
    ]
    occurrences = scan_markers(repository, policy)
    matched_counts: Counter[int] = Counter()
    reviewed: list[dict[str, Any]] = []

    for occurrence in occurrences:
        matches = [
            (position, rule)
            for position, rule in enumerate(rules)
            if isinstance(rule.get("path"), str)
            and fnmatch(cast(str, occurrence["path"]), cast(str, rule["path"]))
            and occurrence["marker_kind"]
            in _strings(rule.get("marker_kinds"), "rule marker kinds are invalid")
        ]
        _require(
            len(matches) == 1,
            f"marker must match exactly one policy rule: {occurrence['path']}:{occurrence['line']}",
        )
        position, rule = matches[0]
        matched_counts[position] += 1
        classification = rule.get("classification")
        _require(
            classification in _CLASSIFICATIONS and classification != "removed_claim",
            f"remaining marker has invalid classification: {rule.get('path')}",
        )
        owner = rule.get("owner")
        reason = rule.get("reason")
        _require(isinstance(owner, str) and owner, "marker rule owner is missing")
        _require(isinstance(reason, str) and reason, "marker rule reason is missing")
        tests = _strings(rule.get("acceptance_tests"), "acceptance tests are invalid")
        if rule.get("public_surface") is True:
            _require(tests, f"public marker lacks acceptance proof: {rule.get('path')}")
        for test in tests:
            _require((repository / test).is_file(), f"acceptance test is missing: {test}")
        reviewed.append(
            {
                **occurrence,
                "classification": classification,
                "owner": owner,
                "public_surface": rule.get("public_surface") is True,
                "reason": reason,
            }
        )

    for position, rule in enumerate(rules):
        expected = rule.get("expected_occurrences")
        _require(
            isinstance(expected, int) and not isinstance(expected, bool) and expected > 0,
            f"rule expected occurrence count is invalid: {rule.get('path')}",
        )
        _require(
            matched_counts[position] == expected,
            f"marker count drift for {rule.get('path')}: expected {expected}, observed {matched_counts[position]}",
        )

    return {
        "classifications": dict(sorted(Counter(item["classification"] for item in reviewed).items())),
        "occurrence_count": len(reviewed),
        "result": "passed",
        "reviewed_occurrences": reviewed,
        "schema_version": "bijux.canon.placeholder_audit.v1",
    }


def _arguments(argv: Sequence[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo-root", type=Path, default=Path.cwd())
    parser.add_argument(
        "--policy", type=Path, default=Path("configs/placeholder-audit.json")
    )
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the governed marker audit and optionally retain its evidence."""
    arguments = _arguments(argv)
    repository = arguments.repo_root.resolve()
    policy = arguments.policy
    if not policy.is_absolute():
        policy = repository / policy
    try:
        report = audit_repository(repository, policy)
    except (OSError, json.JSONDecodeError, PlaceholderAuditError) as error:
        print(f"placeholder audit failed: {error}")
        return 1
    if arguments.output is not None:
        output = arguments.output.resolve()
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    print(json.dumps(report, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
