# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Filesystem adapter for deterministic recursive source discovery."""

from __future__ import annotations

import fnmatch
import hashlib
import os
import stat
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

from bijux_canon_ingest.domain.source_discovery import (
    DiscoveredSource,
    DiscoveryIssue,
    DiscoveryIssueCode,
    DiscoveryPolicy,
    DiscoveryResult,
    DiscoveryRoot,
)

_READ_SIZE = 1024 * 1024
_SNIFF_SIZE = 8192


@dataclass(frozen=True, slots=True)
class _FileIdentity:
    sha256: str
    byte_length: int
    prefix: bytes


@dataclass(slots=True)
class _ScanState:
    sources: list[DiscoveredSource]
    issues: list[DiscoveryIssue]
    content_locations: dict[tuple[str, int], str]
    scanned_entry_count: int = 0
    ignored_entry_count: int = 0


def _portable_order(value: str) -> bytes:
    return value.encode("utf-8", errors="surrogatepass")


def _matches(path: str, patterns: tuple[str, ...]) -> bool:
    candidate = PurePosixPath(path)
    for pattern in patterns:
        variants = [pattern]
        if pattern.startswith("**/"):
            variants.append(pattern[3:])
        if any(
            variant in {"*", "**", "**/*"}
            or fnmatch.fnmatchcase(path, variant)
            or candidate.match(variant)
            for variant in variants
        ):
            return True
    return False


def _excluded(path: str, patterns: tuple[str, ...], *, directory: bool) -> bool:
    if _matches(path, patterns):
        return True
    if not directory:
        return False
    return _matches(f"{path}/__bijux_exclusion_probe__", patterns)


def _inside_root(path: Path, root: Path) -> bool:
    try:
        path.relative_to(root)
    except ValueError:
        return False
    return True


def _relative_target(path: Path, root: Path) -> str:
    return path.relative_to(root).as_posix()


def _issue(
    root: DiscoveryRoot,
    relative_path: str,
    code: DiscoveryIssueCode,
    detail: str,
) -> DiscoveryIssue:
    return DiscoveryIssue(
        root_name=root.name,
        relative_path=relative_path,
        code=code,
        detail=detail,
    )


def _read_file(
    path: Path,
    expected_stat: os.stat_result,
) -> tuple[_FileIdentity | None, DiscoveryIssueCode | None]:
    digest = hashlib.sha256()
    prefix = bytearray()
    try:
        with path.open("rb") as handle:
            before = os.fstat(handle.fileno())
            while True:
                chunk = handle.read(_READ_SIZE)
                if not chunk:
                    break
                digest.update(chunk)
                if len(prefix) < _SNIFF_SIZE:
                    prefix.extend(chunk[: _SNIFF_SIZE - len(prefix)])
            after = os.fstat(handle.fileno())
    except OSError:
        return None, "file_inaccessible"
    stable_fields = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns")
    if any(
        getattr(expected_stat, field) != getattr(before, field)
        or getattr(before, field) != getattr(after, field)
        for field in stable_fields
    ):
        return None, "source_changed"
    return (
        _FileIdentity(
            sha256=digest.hexdigest(),
            byte_length=after.st_size,
            prefix=bytes(prefix),
        ),
        None,
    )


def _media_type(path: str, prefix: bytes) -> str:
    lowered = prefix.lstrip(b"\xef\xbb\xbf\x00\t\n\r ").lower()
    suffix = PurePosixPath(path).suffix.lower()
    if prefix.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if prefix.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if prefix.startswith((b"II*\x00", b"MM\x00*")):
        return "image/tiff"
    if b"%pdf-" in prefix[:1024].lower():
        return "application/pdf"
    if prefix.startswith(b"PK\x03\x04") and suffix == ".docx":
        return "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    if lowered.startswith(b"<!doctype html") or b"<html" in lowered[:1024]:
        return "text/html"
    if lowered.startswith((b"<?xml", b"<article")):
        if b"<article" in lowered:
            return "application/jats+xml"
        return "application/xml"
    try:
        prefix.decode("utf-8")
    except UnicodeDecodeError:
        return "application/octet-stream"
    if b"\x00" in prefix:
        return "application/octet-stream"
    if suffix in {".md", ".markdown", ".mdown", ".mkd"}:
        return "text/markdown"
    return "text/plain"


def _admit_file(
    *,
    root: DiscoveryRoot,
    relative_path: str,
    filesystem_path: Path,
    expected_stat: os.stat_result,
    is_symlink: bool,
    target_relative_path: str | None,
    state: _ScanState,
) -> None:
    identity, failure = _read_file(filesystem_path, expected_stat)
    if identity is None:
        assert failure is not None
        state.issues.append(
            _issue(
                root,
                relative_path,
                failure,
                "file changed while it was read"
                if failure == "source_changed"
                else "file could not be read completely",
            )
        )
        return
    content_key = (identity.sha256, identity.byte_length)
    duplicate_of = state.content_locations.get(content_key)
    source = DiscoveredSource.create(
        root_name=root.name,
        relative_path=relative_path,
        filesystem_path=filesystem_path,
        content_sha256=identity.sha256,
        byte_length=identity.byte_length,
        media_type=_media_type(relative_path, identity.prefix),
        is_symlink=is_symlink,
        target_relative_path=target_relative_path,
        duplicate_of_location_id=duplicate_of,
    )
    state.sources.append(source)
    state.content_locations.setdefault(content_key, source.location_id)


def _scan_directory(
    *,
    root: DiscoveryRoot,
    root_path: Path,
    directory_path: Path,
    relative_directory: PurePosixPath,
    policy: DiscoveryPolicy,
    directory_ancestors: frozenset[tuple[int, int]],
    state: _ScanState,
) -> None:
    relative_value = relative_directory.as_posix()
    try:
        with os.scandir(directory_path) as directory_entries:
            entries = sorted(
                directory_entries, key=lambda entry: _portable_order(entry.name)
            )
    except OSError:
        state.issues.append(
            _issue(
                root,
                "." if relative_value == "." else relative_value,
                "directory_inaccessible",
                "directory entries could not be enumerated",
            )
        )
        return

    for entry in entries:
        state.scanned_entry_count += 1
        relative = relative_directory / entry.name
        relative_path = relative.as_posix()
        try:
            entry_stat = entry.stat(follow_symlinks=False)
        except OSError:
            state.issues.append(
                _issue(
                    root,
                    relative_path,
                    "file_inaccessible",
                    "path metadata could not be read",
                )
            )
            continue

        is_link = stat.S_ISLNK(entry_stat.st_mode)
        is_directory = stat.S_ISDIR(entry_stat.st_mode)
        if _excluded(relative_path, policy.exclude, directory=is_directory):
            state.ignored_entry_count += 1
            continue

        entry_path = Path(entry.path)
        if is_link:
            try:
                resolved = entry_path.resolve(strict=True)
            except OSError:
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "file_inaccessible",
                        "symlink target could not be resolved",
                    )
                )
                continue
            if not _inside_root(resolved, root_path):
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "symlink_escape",
                        "symlink target is outside the declared root",
                    )
                )
                continue
            try:
                target_stat = resolved.stat()
            except OSError:
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "file_inaccessible",
                        "symlink target metadata could not be read",
                    )
                )
                continue
            target_relative = _relative_target(resolved, root_path)
            if stat.S_ISDIR(target_stat.st_mode):
                if _excluded(relative_path, policy.exclude, directory=True):
                    state.ignored_entry_count += 1
                    continue
                if policy.symlink_policy != "all_within_root":
                    state.issues.append(
                        _issue(
                            root,
                            relative_path,
                            "symlink_forbidden",
                            "directory symlink is forbidden by policy",
                        )
                    )
                    continue
                directory_key = (target_stat.st_dev, target_stat.st_ino)
                if directory_key in directory_ancestors:
                    state.issues.append(
                        _issue(
                            root,
                            relative_path,
                            "symlink_cycle",
                            "directory symlink revisits an observed directory",
                        )
                    )
                    continue
                _scan_directory(
                    root=root,
                    root_path=root_path,
                    directory_path=resolved,
                    relative_directory=relative,
                    policy=policy,
                    directory_ancestors=directory_ancestors | {directory_key},
                    state=state,
                )
                continue
            if not stat.S_ISREG(target_stat.st_mode):
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "non_regular_file",
                        "symlink target is not a regular file",
                    )
                )
                continue
            if policy.symlink_policy == "reject":
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "symlink_forbidden",
                        "file symlink is forbidden by policy",
                    )
                )
                continue
            if not _matches(relative_path, policy.include):
                state.ignored_entry_count += 1
                continue
            _admit_file(
                root=root,
                relative_path=relative_path,
                filesystem_path=resolved,
                expected_stat=target_stat,
                is_symlink=True,
                target_relative_path=target_relative,
                state=state,
            )
            continue

        if is_directory:
            directory_key = (entry_stat.st_dev, entry_stat.st_ino)
            if directory_key in directory_ancestors:
                state.issues.append(
                    _issue(
                        root,
                        relative_path,
                        "symlink_cycle",
                        "directory identity was already observed",
                    )
                )
                continue
            _scan_directory(
                root=root,
                root_path=root_path,
                directory_path=entry_path,
                relative_directory=relative,
                policy=policy,
                directory_ancestors=directory_ancestors | {directory_key},
                state=state,
            )
            continue
        if not stat.S_ISREG(entry_stat.st_mode):
            state.issues.append(
                _issue(
                    root,
                    relative_path,
                    "non_regular_file",
                    "path is not a regular file",
                )
            )
            continue
        if not _matches(relative_path, policy.include):
            state.ignored_entry_count += 1
            continue
        _admit_file(
            root=root,
            relative_path=relative_path,
            filesystem_path=entry_path,
            expected_stat=entry_stat,
            is_symlink=False,
            target_relative_path=None,
            state=state,
        )


def discover_directory_sources(policy: DiscoveryPolicy) -> DiscoveryResult:
    """Walk all declared roots without silently omitting inaccessible paths."""

    state = _ScanState(sources=[], issues=[], content_locations={})
    for root in sorted(policy.roots, key=lambda item: _portable_order(item.name)):
        try:
            root_path = root.path.resolve(strict=True)
        except FileNotFoundError:
            state.issues.append(
                _issue(root, ".", "root_missing", "declared root does not exist")
            )
            continue
        except OSError:
            state.issues.append(
                _issue(
                    root,
                    ".",
                    "root_inaccessible",
                    "declared root could not be resolved",
                )
            )
            continue
        try:
            root_stat = root_path.stat()
        except OSError:
            state.issues.append(
                _issue(
                    root,
                    ".",
                    "root_inaccessible",
                    "declared root metadata could not be read",
                )
            )
            continue
        if not stat.S_ISDIR(root_stat.st_mode):
            state.issues.append(
                _issue(
                    root,
                    ".",
                    "root_not_directory",
                    "declared root is not a directory",
                )
            )
            continue
        _scan_directory(
            root=root,
            root_path=root_path,
            directory_path=root_path,
            relative_directory=PurePosixPath(),
            policy=policy,
            directory_ancestors=frozenset({(root_stat.st_dev, root_stat.st_ino)}),
            state=state,
        )

    return DiscoveryResult(
        policy=policy,
        sources=tuple(
            sorted(
                state.sources,
                key=lambda item: (
                    _portable_order(item.root_name),
                    _portable_order(item.relative_path),
                ),
            )
        ),
        issues=tuple(
            sorted(
                state.issues,
                key=lambda item: (
                    _portable_order(item.root_name),
                    _portable_order(item.relative_path),
                    item.code,
                ),
            )
        ),
        scanned_entry_count=state.scanned_entry_count,
        ignored_entry_count=state.ignored_entry_count,
    )


__all__ = ["discover_directory_sources"]
