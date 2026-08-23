# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Canonical corpus commands backed by the shared ingestion runtime."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from bijux_canon_ingest.application.canonical_ingest import (
    CanonicalIngestError,
    CanonicalIngestRequest,
    CanonicalIngestRuntime,
    CorpusSnapshotConfiguration,
)
from bijux_canon_ingest.domain.source_discovery import DiscoveryLimits


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="bijux-canon-ingest corpus")
    subcommands = parser.add_subparsers(dest="operation", required=True)
    build = subcommands.add_parser("build")
    build.add_argument("--root", type=Path, required=True)
    build.add_argument("--root-name", required=True)
    build.add_argument("--corpus-name", required=True)
    build.add_argument("--include", action="append", default=[])
    build.add_argument("--exclude", action="append", default=[])
    build.add_argument(
        "--symlink-policy",
        choices=("reject", "files_within_root", "all_within_root"),
        default="reject",
    )
    build.add_argument("--publish-root", type=Path)
    defaults = DiscoveryLimits()
    build.add_argument("--max-depth", type=int, default=defaults.max_depth)
    build.add_argument("--max-entries", type=int, default=defaults.max_entries)
    build.add_argument("--max-files", type=int, default=defaults.max_files)
    build.add_argument("--max-file-bytes", type=int, default=defaults.max_file_bytes)
    build.add_argument("--max-total-bytes", type=int, default=defaults.max_total_bytes)
    build.add_argument("--max-seconds", type=float, default=defaults.max_seconds)
    build.add_argument(
        "--corpus-lock",
        type=Path,
        help="Explicit corpus.lock.json; adjacent locks are discovered automatically.",
    )
    build.add_argument("--out", type=Path)
    return parser


def run_corpus_commands(argv: list[str]) -> int:
    """Run canonical corpus ingestion and emit its shared response schema."""

    args = _parser().parse_args(argv[1:])
    try:
        result = CanonicalIngestRuntime().ingest(
            CanonicalIngestRequest(
                root_path=args.root,
                root_name=args.root_name,
                configuration=CorpusSnapshotConfiguration(
                    corpus_name=args.corpus_name,
                    discovery_limits=DiscoveryLimits(
                        max_depth=args.max_depth,
                        max_entries=args.max_entries,
                        max_files=args.max_files,
                        max_file_bytes=args.max_file_bytes,
                        max_total_bytes=args.max_total_bytes,
                        max_seconds=args.max_seconds,
                    ),
                ),
                include=tuple(args.include) or ("**/*",),
                exclude=tuple(args.exclude),
                symlink_policy=args.symlink_policy,
                corpus_lock_path=args.corpus_lock,
                publication_root=args.publish_root,
            )
        )
    except (CanonicalIngestError, OSError, ValueError) as error:
        print(str(error), file=sys.stderr)
        return 2
    content = (
        json.dumps(
            result.manifest(),
            sort_keys=True,
            separators=(",", ":"),
            ensure_ascii=False,
            allow_nan=False,
        )
        + "\n"
    )
    if args.out is None:
        sys.stdout.write(content)
    else:
        args.out.write_text(content, encoding="utf-8")
    return 0


__all__ = ["run_corpus_commands"]
