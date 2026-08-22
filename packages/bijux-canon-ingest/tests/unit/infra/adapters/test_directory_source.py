# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

from __future__ import annotations

import os
from pathlib import Path

import pytest

from bijux_canon_ingest import (
    DiscoveryPolicy,
    DiscoveryRoot,
    discover_sources,
)


def _write_tree(root: Path) -> None:
    (root / "papers").mkdir(parents=True)
    (root / "ignored").mkdir()
    (root / "README.md").write_text("# Evidence\n", encoding="utf-8")
    (root / "papers" / "article.xml").write_text(
        "<?xml version='1.0'?><article><body>DNA</body></article>",
        encoding="utf-8",
    )
    (root / "papers" / "copy.txt").write_text("# Evidence\n", encoding="utf-8")
    (root / "papers" / "paper.pdf").write_bytes(b"%PDF-1.7\nreal payload")
    (root / "ignored" / "draft.md").write_text("draft", encoding="utf-8")


def test_discovery_is_recursive_filtered_ordered_and_content_aware(
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    _write_tree(root)
    policy = DiscoveryPolicy(
        roots=(DiscoveryRoot("research", root),),
        exclude=("ignored/**",),
    )

    first = discover_sources(policy)
    second = discover_sources(policy)

    assert first.manifest() == second.manifest()
    assert first.complete is True
    assert [source.relative_path for source in first.sources] == [
        "README.md",
        "papers/article.xml",
        "papers/copy.txt",
        "papers/paper.pdf",
    ]
    assert [source.media_type for source in first.sources] == [
        "text/markdown",
        "application/jats+xml",
        "text/plain",
        "application/pdf",
    ]
    assert first.duplicate_count == 1
    assert first.sources[2].duplicate_of_location_id == first.sources[0].location_id
    assert first.ignored_entry_count == 1


def test_discovery_identity_survives_root_relocation(tmp_path: Path) -> None:
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    _write_tree(first_root)
    _write_tree(second_root)

    first = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot("research", first_root),),
            include=("**/*.md", "**/*.xml", "**/*.pdf", "**/*.txt"),
            exclude=("ignored/**",),
        )
    )
    second = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot("research", second_root),),
            include=("**/*.md", "**/*.xml", "**/*.pdf", "**/*.txt"),
            exclude=("ignored/**",),
        )
    )

    assert first.manifest() == second.manifest()
    assert first.sources[0].filesystem_path != second.sources[0].filesystem_path


def test_missing_and_non_directory_roots_are_typed_incomplete_outcomes(
    tmp_path: Path,
) -> None:
    file_root = tmp_path / "one.txt"
    file_root.write_text("one", encoding="utf-8")
    result = discover_sources(
        DiscoveryPolicy(
            roots=(
                DiscoveryRoot("missing", tmp_path / "missing"),
                DiscoveryRoot("regular-file", file_root),
            )
        )
    )

    assert result.complete is False
    assert [(issue.root_name, issue.code) for issue in result.issues] == [
        ("missing", "root_missing"),
        ("regular-file", "root_not_directory"),
    ]
    assert result.sources == ()


def test_symlink_policy_rejects_escape_and_can_admit_internal_file(
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    source = root / "source.txt"
    source.write_text("stable", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("outside", encoding="utf-8")
    internal_link = root / "z-internal.txt"
    external_link = root / "z-outside.txt"
    try:
        internal_link.symlink_to(source)
        external_link.symlink_to(outside)
    except OSError as error:
        pytest.skip(f"filesystem does not support test symlinks: {error}")

    rejected = discover_sources(
        DiscoveryPolicy(roots=(DiscoveryRoot("research", root),))
    )
    admitted = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot("research", root),),
            symlink_policy="files_within_root",
        )
    )

    assert [(issue.relative_path, issue.code) for issue in rejected.issues] == [
        ("z-internal.txt", "symlink_forbidden"),
        ("z-outside.txt", "symlink_escape"),
    ]
    assert [(issue.relative_path, issue.code) for issue in admitted.issues] == [
        ("z-outside.txt", "symlink_escape")
    ]
    internal = next(
        source
        for source in admitted.sources
        if source.relative_path == "z-internal.txt"
    )
    assert internal.is_symlink is True
    assert internal.target_relative_path == "source.txt"
    assert internal.duplicate_of_location_id == admitted.sources[0].location_id


def test_directory_symlink_cycles_are_rejected_without_recursion(
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    child = root / "child"
    child.mkdir(parents=True)
    (child / "paper.txt").write_text("paper", encoding="utf-8")
    cycle = child / "root"
    try:
        cycle.symlink_to(root, target_is_directory=True)
    except OSError as error:
        pytest.skip(f"filesystem does not support test symlinks: {error}")

    result = discover_sources(
        DiscoveryPolicy(
            roots=(DiscoveryRoot("research", root),),
            symlink_policy="all_within_root",
        )
    )

    assert [source.relative_path for source in result.sources] == ["child/paper.txt"]
    assert [(issue.relative_path, issue.code) for issue in result.issues] == [
        ("child/root", "symlink_cycle")
    ]
    assert result.complete is True


def test_policy_rejects_ambiguous_roots_and_nonportable_globs(tmp_path: Path) -> None:
    root = DiscoveryRoot("research", tmp_path)
    with pytest.raises(ValueError, match="unique"):
        DiscoveryPolicy(roots=(root, root))
    with pytest.raises(ValueError, match="portable"):
        DiscoveryPolicy(roots=(root,), include=("../*.pdf",))


def test_discovery_rejects_non_regular_files_without_reading_them(
    tmp_path: Path,
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    fifo = root / "stream.txt"
    os.mkfifo(fifo)

    result = discover_sources(DiscoveryPolicy(roots=(DiscoveryRoot("research", root),)))

    assert result.sources == ()
    assert [(issue.relative_path, issue.code) for issue in result.issues] == [
        ("stream.txt", "non_regular_file")
    ]


def test_discovery_rejects_file_swapped_to_external_symlink_before_read(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "documents"
    root.mkdir()
    source = root / "paper.txt"
    source.write_text("authorized bytes", encoding="utf-8")
    outside = tmp_path / "outside.txt"
    outside.write_text("unauthorized bytes", encoding="utf-8")
    original_open = Path.open
    swapped = False

    def swap_before_open(path: Path, *args: object, **kwargs: object):
        nonlocal swapped
        if path == source and not swapped:
            swapped = True
            source.unlink()
            source.symlink_to(outside)
        return original_open(path, *args, **kwargs)

    monkeypatch.setattr(Path, "open", swap_before_open)
    result = discover_sources(DiscoveryPolicy(roots=(DiscoveryRoot("research", root),)))

    assert swapped is True
    assert result.sources == ()
    assert [(issue.relative_path, issue.code) for issue in result.issues] == [
        ("paper.txt", "source_changed")
    ]
