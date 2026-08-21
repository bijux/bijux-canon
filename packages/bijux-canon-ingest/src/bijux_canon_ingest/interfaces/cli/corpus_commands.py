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
)
from bijux_canon_ingest.domain.corpus_snapshot import CorpusSnapshotConfiguration


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
                configuration=CorpusSnapshotConfiguration(corpus_name=args.corpus_name),
                include=tuple(args.include) or ("**/*",),
                exclude=tuple(args.exclude),
                symlink_policy=args.symlink_policy,
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
