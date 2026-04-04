from __future__ import annotations

from pathlib import Path
import sys


sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from bijux_canon_dev.docs.mkdocs_config import _rewrite_config


def test_rendered_serve_config_rewrites_relative_watch_paths(tmp_path) -> None:
    source_root = tmp_path / "repo"
    source_root.mkdir()
    source_config = source_root / "mkdocs.yml"
    output_config = tmp_path / "artifacts" / "mkdocs.serve.yml"
    docs_dir = source_root / "docs"
    shared_config = source_root / "mkdocs.shared.yml"

    docs_dir.mkdir()
    shared_config.write_text("strict: true\n", encoding="utf-8")
    source_config.write_text(
        "\n".join(
            [
                "INHERIT: mkdocs.shared.yml",
                "docs_dir: docs",
                "site_dir: site",
                "site_url: https://example.invalid/",
                "watch:",
                "  - docs",
                "  - docs/assets",
                "  - mkdocs.yml",
                "  - https://example.invalid/keep-me",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    _rewrite_config(
        source_config=source_config,
        output_config=output_config,
        docs_dir=docs_dir,
        site_dir=tmp_path / "site",
        site_url="http://127.0.0.1:8001/",
        inherit_config=shared_config,
    )

    rendered = output_config.read_text(encoding="utf-8")

    assert f"INHERIT: {shared_config.resolve()}" in rendered
    assert f"docs_dir: {docs_dir.resolve()}" in rendered
    assert f"  - {(source_root / 'docs').resolve()}" in rendered
    assert f"  - {(source_root / 'docs/assets').resolve()}" in rendered
    assert f"  - {(source_root / 'mkdocs.yml').resolve()}" in rendered
    assert "  - https://example.invalid/keep-me" in rendered
