# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Stable values for deterministic filesystem source discovery."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
from pathlib import Path, PurePosixPath
from typing import Literal, get_args

SymlinkPolicy = Literal["reject", "files_within_root", "all_within_root"]
DiscoveryIssueCode = Literal[
    "directory_inaccessible",
    "file_inaccessible",
    "non_regular_file",
    "root_inaccessible",
    "root_missing",
    "root_not_directory",
    "source_changed",
    "symlink_cycle",
    "symlink_escape",
    "symlink_forbidden",
]

_INCOMPLETE_CODES: frozenset[DiscoveryIssueCode] = frozenset(
    {
        "directory_inaccessible",
        "file_inaccessible",
        "root_inaccessible",
        "root_missing",
        "root_not_directory",
        "source_changed",
    }
)
_ISSUE_CODES: frozenset[str] = frozenset(get_args(DiscoveryIssueCode))


def _canonical_json(value: object) -> bytes:
    return json.dumps(
        value,
        sort_keys=True,
        separators=(",", ":"),
        ensure_ascii=False,
        allow_nan=False,
    ).encode("utf-8")


def _sha256_identity(value: object) -> str:
    return f"sha256:{hashlib.sha256(_canonical_json(value)).hexdigest()}"


def _validate_relative_path(value: str) -> None:
    path = PurePosixPath(value)
    if not value or value.startswith("/") or "\\" in value:
        raise ValueError("relative_path must be a non-empty portable relative path")
    if any(part in {"", ".", ".."} for part in path.parts):
        raise ValueError(
            "relative_path must not contain empty, dot, or parent segments"
        )
    if path.as_posix() != value:
        raise ValueError("relative_path must use canonical POSIX spelling")


@dataclass(frozen=True, slots=True)
class DiscoveryRoot:
    """A filesystem root paired with a stable, user-declared logical name."""

    name: str
    path: Path

    def __post_init__(self) -> None:
        if not self.name or self.name in {".", ".."}:
            raise ValueError("DiscoveryRoot.name must be a stable non-empty name")
        if any(character in self.name for character in ("/", "\\", "\x00")):
            raise ValueError("DiscoveryRoot.name must not contain path separators")


@dataclass(frozen=True, slots=True)
class DiscoveryPolicy:
    """Portable include, exclude, and symlink rules for one discovery pass."""

    roots: tuple[DiscoveryRoot, ...]
    include: tuple[str, ...] = ("**/*",)
    exclude: tuple[str, ...] = ()
    symlink_policy: SymlinkPolicy = "reject"

    def __post_init__(self) -> None:
        if not self.roots:
            raise ValueError("DiscoveryPolicy.roots must not be empty")
        names = [root.name for root in self.roots]
        if len(names) != len(set(names)):
            raise ValueError("DiscoveryPolicy root names must be unique")
        for field_name, patterns in (
            ("include", self.include),
            ("exclude", self.exclude),
        ):
            if field_name == "include" and not patterns:
                raise ValueError("DiscoveryPolicy.include must not be empty")
            for pattern in patterns:
                if (
                    not pattern
                    or pattern.startswith("/")
                    or "\\" in pattern
                    or ".." in PurePosixPath(pattern).parts
                ):
                    raise ValueError(
                        f"DiscoveryPolicy.{field_name} patterns must be portable relative globs"
                    )
        if self.symlink_policy not in {
            "reject",
            "files_within_root",
            "all_within_root",
        }:
            raise ValueError("unsupported symlink policy")


@dataclass(frozen=True, slots=True)
class DiscoveredSource:
    """An immutable content identity at one stable relative location."""

    root_name: str
    relative_path: str
    filesystem_path: Path
    location_id: str
    content_sha256: str
    byte_length: int
    media_type: str
    is_symlink: bool
    target_relative_path: str | None = None
    duplicate_of_location_id: str | None = None

    def __post_init__(self) -> None:
        _validate_relative_path(self.relative_path)
        if self.target_relative_path is not None:
            _validate_relative_path(self.target_relative_path)
        if not self.location_id.startswith("sha256:") or len(self.location_id) != 71:
            raise ValueError("location_id must be a sha256 identity")
        if len(self.content_sha256) != 64 or any(
            character not in "0123456789abcdef" for character in self.content_sha256
        ):
            raise ValueError("content_sha256 must be lowercase hexadecimal")
        if self.byte_length < 0:
            raise ValueError("byte_length must not be negative")
        if "/" not in self.media_type:
            raise ValueError("media_type must be a type/subtype value")

    @classmethod
    def create(
        cls,
        *,
        root_name: str,
        relative_path: str,
        filesystem_path: Path,
        content_sha256: str,
        byte_length: int,
        media_type: str,
        is_symlink: bool,
        target_relative_path: str | None = None,
        duplicate_of_location_id: str | None = None,
    ) -> DiscoveredSource:
        location_id = _sha256_identity(
            {
                "identity_type": "bijux.canon.ingest.source_location.v1",
                "relative_path": relative_path,
                "root_name": root_name,
            }
        )
        return cls(
            root_name=root_name,
            relative_path=relative_path,
            filesystem_path=filesystem_path,
            location_id=location_id,
            content_sha256=content_sha256,
            byte_length=byte_length,
            media_type=media_type,
            is_symlink=is_symlink,
            target_relative_path=target_relative_path,
            duplicate_of_location_id=duplicate_of_location_id,
        )

    def identity_payload(self) -> dict[str, object]:
        """Return the stable fields admitted to the discovery manifest."""

        return {
            "byte_length": self.byte_length,
            "content_sha256": self.content_sha256,
            "duplicate_of_location_id": self.duplicate_of_location_id,
            "is_symlink": self.is_symlink,
            "location_id": self.location_id,
            "media_type": self.media_type,
            "relative_path": self.relative_path,
            "root_name": self.root_name,
            "target_relative_path": self.target_relative_path,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryIssue:
    """A stable typed rejection or incomplete-observation outcome."""

    root_name: str
    relative_path: str
    code: DiscoveryIssueCode
    detail: str

    def __post_init__(self) -> None:
        if self.relative_path != ".":
            _validate_relative_path(self.relative_path)
        if self.code not in _ISSUE_CODES:
            raise ValueError("unsupported discovery issue code")
        if not self.detail:
            raise ValueError("DiscoveryIssue.detail must not be empty")

    @property
    def prevents_complete_snapshot(self) -> bool:
        return self.code in _INCOMPLETE_CODES

    def identity_payload(self) -> dict[str, str]:
        return {
            "code": self.code,
            "detail": self.detail,
            "relative_path": self.relative_path,
            "root_name": self.root_name,
        }


@dataclass(frozen=True, slots=True)
class DiscoveryResult:
    """Deterministically ordered sources, rejections, and scan accounting."""

    policy: DiscoveryPolicy
    sources: tuple[DiscoveredSource, ...]
    issues: tuple[DiscoveryIssue, ...]
    scanned_entry_count: int
    ignored_entry_count: int

    def __post_init__(self) -> None:
        source_order = [(item.root_name, item.relative_path) for item in self.sources]
        issue_order = [
            (item.root_name, item.relative_path, item.code) for item in self.issues
        ]
        if source_order != sorted(source_order):
            raise ValueError("DiscoveryResult.sources must use canonical order")
        if issue_order != sorted(issue_order):
            raise ValueError("DiscoveryResult.issues must use canonical order")
        if self.scanned_entry_count < 0 or self.ignored_entry_count < 0:
            raise ValueError("discovery counts must not be negative")

    @property
    def complete(self) -> bool:
        """Whether every included path was observed sufficiently for a snapshot."""

        return not any(issue.prevents_complete_snapshot for issue in self.issues)

    @property
    def duplicate_count(self) -> int:
        return sum(
            source.duplicate_of_location_id is not None for source in self.sources
        )

    def manifest(self) -> dict[str, object]:
        """Return a relocation-independent canonical discovery manifest."""

        payload: dict[str, object] = {
            "complete": self.complete,
            "ignored_entry_count": self.ignored_entry_count,
            "issues": [issue.identity_payload() for issue in self.issues],
            "policy": {
                "exclude": list(self.policy.exclude),
                "include": list(self.policy.include),
                "root_names": sorted(root.name for root in self.policy.roots),
                "symlink_policy": self.policy.symlink_policy,
            },
            "scanned_entry_count": self.scanned_entry_count,
            "schema_version": "bijux.canon.ingest.discovery.v1",
            "sources": [source.identity_payload() for source in self.sources],
        }
        return {"manifest_sha256": _sha256_identity(payload), **payload}


__all__ = [
    "DiscoveredSource",
    "DiscoveryIssue",
    "DiscoveryIssueCode",
    "DiscoveryPolicy",
    "DiscoveryResult",
    "DiscoveryRoot",
    "SymlinkPolicy",
]
