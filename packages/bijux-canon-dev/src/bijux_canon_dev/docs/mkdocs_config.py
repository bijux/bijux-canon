from __future__ import annotations

import argparse
from pathlib import Path


def _rewrite_watch_path(path_text: str, *, source_root: Path) -> str:
    stripped = path_text.strip()
    if not stripped:
        return path_text
    candidate = Path(stripped)
    if candidate.is_absolute() or "://" in stripped:
        return path_text
    return str((source_root / candidate).resolve())


def _rewrite_config(
    *,
    source_config: Path,
    output_config: Path,
    docs_dir: Path | None = None,
    site_dir: Path | None = None,
    site_url: str | None = None,
    inherit_config: Path | None = None,
) -> None:
    lines = source_config.read_text(encoding="utf-8").splitlines()
    rewritten: list[str] = []
    wrote_docs_dir = False
    wrote_site_dir = False
    wrote_site_url = False
    wrote_inherit = False
    in_watch_block = False
    source_root = source_config.resolve().parent

    for line in lines:
        stripped = line.strip()

        if in_watch_block:
            if line.startswith("  - "):
                watch_path = line.removeprefix("  - ")
                rewritten.append(
                    f"  - {_rewrite_watch_path(watch_path, source_root=source_root)}"
                )
                continue
            if stripped and not line.startswith(" ") or not stripped:
                in_watch_block = False

        if line.startswith("watch:"):
            rewritten.append(line)
            in_watch_block = True
        elif line.startswith("INHERIT:") and inherit_config is not None:
            rewritten.append(f"INHERIT: {inherit_config.resolve()}")
            wrote_inherit = True
        elif line.startswith("docs_dir:") and docs_dir is not None:
            rewritten.append(f"docs_dir: {docs_dir.resolve()}")
            wrote_docs_dir = True
        elif line.startswith("site_dir:") and site_dir is not None:
            rewritten.append(f"site_dir: {site_dir.resolve()}")
            wrote_site_dir = True
        elif line.startswith("site_url:") and site_url is not None:
            rewritten.append(f"site_url: {site_url}")
            wrote_site_url = True
        else:
            rewritten.append(line)

    if inherit_config is not None and not wrote_inherit:
        rewritten.insert(0, f"INHERIT: {inherit_config.resolve()}")
    if docs_dir is not None and not wrote_docs_dir:
        rewritten.append(f"docs_dir: {docs_dir.resolve()}")
    if site_dir is not None and not wrote_site_dir:
        rewritten.append(f"site_dir: {site_dir.resolve()}")
    if site_url is not None and not wrote_site_url:
        rewritten.append(f"site_url: {site_url}")

    output_config.parent.mkdir(parents=True, exist_ok=True)
    output_config.write_text("\n".join(rewritten) + "\n", encoding="utf-8")


def prepare_source(args: argparse.Namespace) -> int:
    _rewrite_config(
        source_config=args.source_config,
        output_config=args.output_config,
        docs_dir=args.docs_source_dir,
    )
    return 0


def render_serve_config(args: argparse.Namespace) -> int:
    inherit_config = args.inherit_config if args.inherit_config else None
    _rewrite_config(
        source_config=args.source_config,
        output_config=args.output_config,
        docs_dir=args.docs_dir,
        site_dir=args.site_dir,
        site_url=args.site_url,
        inherit_config=inherit_config,
    )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Rewrite MkDocs config files for repository workflows."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    prepare = subparsers.add_parser(
        "prepare-source", help="Rewrite docs_dir for a copied docs source tree."
    )
    prepare.add_argument("--source-config", type=Path, required=True)
    prepare.add_argument("--output-config", type=Path, required=True)
    prepare.add_argument("--docs-source-dir", type=Path, required=True)
    prepare.set_defaults(func=prepare_source)

    render = subparsers.add_parser(
        "render-serve-config", help="Rewrite serve-specific MkDocs settings."
    )
    render.add_argument("--source-config", type=Path, required=True)
    render.add_argument("--output-config", type=Path, required=True)
    render.add_argument("--docs-dir", type=Path, required=True)
    render.add_argument("--site-dir", type=Path, required=True)
    render.add_argument("--site-url", required=True)
    render.add_argument("--inherit-config", type=Path)
    render.set_defaults(func=render_serve_config)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
