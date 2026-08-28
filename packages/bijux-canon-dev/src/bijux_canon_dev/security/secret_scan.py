"""Scan tracked repository source for high-confidence credential material."""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import stat
import subprocess
from typing import Any

_PATTERNS = (
    ("aws-access-key", re.compile(rb"\b(?:AKIA|ASIA)[0-9A-Z]{16}\b")),
    ("github-token", re.compile(rb"\bgh[pousr]_[A-Za-z0-9]{36,255}\b")),
    ("github-fine-grained-token", re.compile(rb"\bgithub_pat_[A-Za-z0-9_]{40,255}\b")),
    ("openai-api-key", re.compile(rb"\bsk-(?:proj-)?[A-Za-z0-9_-]{32,255}\b")),
    (
        "private-key",
        re.compile(rb"-----BEGIN (?:RSA |EC |OPENSSH |DSA )?PRIVATE KEY-----"),
    ),
)


def _git(root: Path, *arguments: str) -> bytes:
    process = subprocess.run(  # noqa: S603 - fixed git executable and owned arguments
        ("git", "-C", str(root), *arguments),
        check=False,
        capture_output=True,
    )
    if process.returncode != 0:
        detail = process.stderr.decode("utf-8", errors="replace").strip()
        raise RuntimeError(f"git {' '.join(arguments)} failed: {detail}")
    return process.stdout


def _tracked_paths(root: Path) -> list[str]:
    raw = _git(root, "ls-files", "-z")
    return sorted(
        part.decode("utf-8", errors="strict") for part in raw.split(b"\0") if part
    )


def _line_number(content: bytes, offset: int) -> int:
    return content.count(b"\n", 0, offset) + 1


def scan_repository(root: Path) -> dict[str, Any]:
    """Return a deterministic, secret-safe report for tracked regular files."""
    root = root.resolve(strict=True)
    commit = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    dirty = bool(_git(root, "status", "--porcelain", "--untracked-files=no"))
    findings: list[dict[str, Any]] = []
    scanned: list[dict[str, Any]] = []
    binary_files: list[str] = []

    for relative_path in _tracked_paths(root):
        candidate = root / relative_path
        mode = candidate.lstat().st_mode
        if not stat.S_ISREG(mode):
            raise RuntimeError(f"tracked path is not a regular file: {relative_path}")
        content = candidate.read_bytes()
        digest = hashlib.sha256(content).hexdigest()
        scanned.append(
            {"path": relative_path, "sha256": digest, "size_bytes": len(content)}
        )
        if b"\0" in content[:8192]:
            binary_files.append(relative_path)
            continue
        for kind, pattern in _PATTERNS:
            for match in pattern.finditer(content):
                findings.append(
                    {
                        "kind": kind,
                        "line": _line_number(content, match.start()),
                        "path": relative_path,
                    }
                )

    findings.sort(key=lambda item: (item["path"], item["line"], item["kind"]))
    return {
        "schema_version": 1,
        "source": {"commit": commit, "tracked_worktree_dirty": dirty},
        "summary": {
            "binary_files_skipped": len(binary_files),
            "findings": len(findings),
            "tracked_files_scanned": len(scanned),
        },
        "binary_files_skipped": binary_files,
        "findings": findings,
        "scanned_files": scanned,
    }


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Scan tracked regular files for high-confidence credential material."
    )
    parser.add_argument("--repository", type=Path, default=Path.cwd())
    parser.add_argument("--output", type=Path, required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    """Run the tracked-source credential scanner."""
    arguments = _parser().parse_args(argv)
    try:
        report = scan_repository(arguments.repository)
        arguments.output.parent.mkdir(parents=True, exist_ok=True)
        arguments.output.write_text(
            json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8"
        )
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: tracked-source credential scan failed: {exc}")
        return 2

    count = report["summary"]["findings"]
    if count:
        print(f"FAIL: {count} potential credential(s) found; see {arguments.output}")
        return 1
    print(
        "OK: no high-confidence credentials found in "
        f"{report['summary']['tracked_files_scanned']} tracked files."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
