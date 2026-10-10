from __future__ import annotations

from html.parser import HTMLParser
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import urljoin, urlparse

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
SITE_URL = "https://bijux.io/bijux-canon/"
MERMAID_RESERVED_IDS = {
    "class",
    "classdef",
    "click",
    "default",
    "end",
    "graph",
    "linkstyle",
    "style",
    "subgraph",
}


class _RenderedNavigationParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.depth = 0
        self.navigation_depth: int | None = None
        self.variant: str | None = None
        self.links: list[tuple[str, bool]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag not in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            self.depth += 1
        values = dict(attrs)
        if tag == "nav" and values.get("id") == "bijux-navigation":
            self.navigation_depth = self.depth
            self.variant = values.get("data-bijux-nav-variant")
        if (
            self.navigation_depth is not None
            and tag == "a"
            and "md-nav__link" in str(values.get("class", "")).split()
        ):
            self.links.append(
                (str(values.get("href", "")), values.get("aria-current") == "page")
            )

    def handle_endtag(self, tag: str) -> None:
        if tag == "nav" and self.navigation_depth == self.depth:
            self.navigation_depth = None
        self.depth = max(0, self.depth - 1)


def _authored_routes(value: object) -> list[str]:
    if isinstance(value, str):
        if not value.endswith(".md"):
            return []
        return [
            value.removesuffix("index.md")
            if value.endswith("index.md")
            else value.removesuffix(".md") + "/"
        ]
    if isinstance(value, dict):
        return [route for child in value.values() for route in _authored_routes(child)]
    if isinstance(value, list):
        return [route for child in value for route in _authored_routes(child)]
    return []


@pytest.fixture(scope="session")
def rendered_docs(tmp_path_factory: pytest.TempPathFactory) -> Path:
    site_dir = tmp_path_factory.mktemp("docs-site")
    subprocess.run(
        [
            sys.executable,
            "-m",
            "mkdocs",
            "build",
            "--quiet",
            "--config-file",
            str(REPO_ROOT / "mkdocs.yml"),
            "--site-dir",
            str(site_dir),
        ],
        cwd=REPO_ROOT,
        check=True,
    )
    return site_dir


@pytest.mark.parametrize(
    "relative_path",
    [
        "index.html",
        "01-bijux-canon/index.html",
        "01-bijux-canon/foundation/package-map/index.html",
        "01-bijux-canon/operations/review-expectations/index.html",
        "03-bijux-canon-index/index.html",
        "03-bijux-canon-index/architecture/code-navigation/index.html",
        "03-bijux-canon-index/interfaces/index.html",
        "03-bijux-canon-index/interfaces/api-surface/index.html",
        "02-bijux-canon-ingest/operations/index.html",
        "04-bijux-canon-reason/operations/index.html",
        "05-bijux-canon-agent/index.html",
        "07-bijux-canon-maintain/index.html",
        "07-bijux-canon-maintain/bijux-canon-dev/security-gates/index.html",
        "07-bijux-canon-maintain/makes/package-dispatch/index.html",
        "07-bijux-canon-maintain/gh-workflows/release-workflows/index.html",
        "08-compat-packages/index.html",
        "08-compat-packages/catalog/bijux-agent/index.html",
        "08-compat-packages/migration/retirement-playbook/index.html",
    ],
)
def test_native_navigation_retains_every_authored_route_and_current_page(
    rendered_docs: Path,
    relative_path: str,
) -> None:
    parser = _RenderedNavigationParser()
    parser.feed((rendered_docs / relative_path).read_text(encoding="utf-8"))
    assert parser.variant == "complete"
    document = yaml.compose((REPO_ROOT / "mkdocs.yml").read_text(encoding="utf-8"))
    assert isinstance(document, yaml.MappingNode)
    navigation = next(value for key, value in document.value if key.value == "nav")
    config = {"nav": yaml.safe_load(yaml.serialize(navigation))}
    expected = [urljoin(SITE_URL, route) for route in _authored_routes(config["nav"])]
    page_url = urljoin(SITE_URL, relative_path.removesuffix("index.html"))
    actual = [urljoin(page_url, href) for href, _ in parser.links]
    assert actual == expected
    active = [urljoin(page_url, href) for href, current in parser.links if current]
    assert active
    assert set(active) == {page_url}
    for target in actual:
        relative = urlparse(target).path.removeprefix("/bijux-canon/")
        assert (rendered_docs / relative / "index.html").is_file()


def test_hub_navigation_excludes_private_sites(rendered_docs: Path) -> None:
    text = (rendered_docs / "index.html").read_text(encoding="utf-8")
    assert 'href="https://bijux.io/bijux-core/"' in text
    assert "bijux-genomics" not in text


def test_authored_mermaid_diagrams_avoid_reserved_node_names() -> None:
    violations = []
    for path in (REPO_ROOT / "docs").rglob("*.md"):
        for block in re.findall(
            r"```mermaid\n([\s\S]*?)\n```", path.read_text(encoding="utf-8")
        ):
            for node in re.findall(
                r"^\s*([A-Za-z_][A-Za-z0-9_-]*)\s*\[", block, re.MULTILINE
            ):
                if node.lower() in MERMAID_RESERVED_IDS:
                    violations.append((str(path.relative_to(REPO_ROOT)), node))
    assert not violations
