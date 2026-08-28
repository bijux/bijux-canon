# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic semantic extraction from admitted HTML documents."""

from __future__ import annotations

import hashlib
from collections.abc import Iterator
from dataclasses import dataclass, field
from html.parser import HTMLParser

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    HtmlBlockRole,
    HtmlDocumentMetadata,
    HtmlLink,
    ParsedHtmlBlock,
    ParsedHtmlDocument,
    SourceLocator,
)

_PARSER_NAME = "bijux-canon-ingest-html"
_PARSER_VERSION = "1"


def parser_identity() -> tuple[str, str, str]:
    """Return the extraction contract that governs HTML reuse."""

    return _PARSER_NAME, _PARSER_VERSION, "bijux.canon.ingest.parsed_html_document.v1"


_VOID_ELEMENTS = frozenset(
    {
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
    }
)
_NOISE_ELEMENTS = frozenset(
    {"aside", "nav", "noscript", "script", "style", "svg", "template"}
)
_NOISE_MARKERS = (
    "carousel",
    "figure-lightbox",
    "metrics",
    "nav-",
    "navigation",
    "related",
    "social",
    "toolbar",
)
_BLOCK_ELEMENTS = frozenset({"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "table"})


@dataclass(slots=True, eq=False)
class _Node:
    tag: str
    attrs: dict[str, str]
    parent: _Node | None
    children: list[_Node | str] = field(default_factory=list)


class _TreeBuilder(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Node("document", {}, None)
        self._stack = [self.root]

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(
            tag.lower(),
            {name.lower(): value or "" for name, value in attrs},
            self._stack[-1],
        )
        self._stack[-1].children.append(node)
        if node.tag not in _VOID_ELEMENTS:
            self._stack.append(node)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        node = _Node(
            tag.lower(),
            {name.lower(): value or "" for name, value in attrs},
            self._stack[-1],
        )
        self._stack[-1].children.append(node)

    def handle_endtag(self, tag: str) -> None:
        lowered = tag.lower()
        for index in range(len(self._stack) - 1, 0, -1):
            if self._stack[index].tag == lowered:
                del self._stack[index:]
                return

    def handle_data(self, data: str) -> None:
        self._stack[-1].children.append(data)


def _walk(node: _Node) -> Iterator[_Node]:
    yield node
    for child in node.children:
        if isinstance(child, _Node):
            yield from _walk(child)


def _text_nodes(node: _Node) -> Iterator[str]:
    for child in node.children:
        if isinstance(child, str):
            yield child
        else:
            yield from _text_nodes(child)


def _normalized_text(node: _Node) -> str:
    return " ".join(" ".join(_text_nodes(node)).split())


def _source_text(node: _Node) -> str:
    return "".join(_text_nodes(node))


def _dom_path(node: _Node) -> str:
    parts: list[str] = []
    current = node
    while current.parent is not None:
        siblings = [
            child
            for child in current.parent.children
            if isinstance(child, _Node) and child.tag == current.tag
        ]
        suffix = f"[{siblings.index(current) + 1}]" if len(siblings) > 1 else ""
        parts.append(f"{current.tag}{suffix}")
        current = current.parent
    return "/" + "/".join(reversed(parts))


def _ancestors(node: _Node) -> Iterator[_Node]:
    current = node.parent
    while current is not None:
        yield current
        current = current.parent


def _marker(node: _Node) -> str:
    return " ".join((node.attrs.get("id", ""), node.attrs.get("class", ""))).lower()


def _is_noise(node: _Node) -> bool:
    return any(
        item.tag in _NOISE_ELEMENTS
        or any(marker in _marker(item) for marker in _NOISE_MARKERS)
        for item in (node, *_ancestors(node))
    )


def _has_ancestor(node: _Node, tag: str) -> bool:
    return any(item.tag == tag for item in _ancestors(node))


def _has_ancestor_marker(node: _Node, marker: str) -> bool:
    return any(marker in _marker(item) for item in _ancestors(node))


def _metadata(root: _Node) -> HtmlDocumentMetadata:
    nodes = list(_walk(root))
    html = next((node for node in nodes if node.tag == "html"), None)
    meta = tuple(
        (node.attrs.get("name", "").lower(), node.attrs.get("content", ""))
        for node in nodes
        if node.tag == "meta" and node.attrs.get("name") and node.attrs.get("content")
    )

    def first(name: str) -> str:
        return next((value for key, value in meta if key == name), "")

    canonical = next(
        (
            node.attrs.get("href")
            for node in nodes
            if node.tag == "link"
            and "canonical" in node.attrs.get("rel", "").lower().split()
            and node.attrs.get("href")
        ),
        None,
    )
    try:
        return HtmlDocumentMetadata(
            title=first("citation_title"),
            authors=tuple(value for name, value in meta if name == "citation_author"),
            doi=first("citation_doi"),
            language=html.attrs.get("lang") if html is not None else None,
            canonical_url=canonical,
            raw_meta=meta,
        )
    except ValueError as error:
        raise DocumentParseError(
            "missing_required_metadata",
            "HTML requires citation title, author, and DOI metadata",
        ) from error


def _links(node: _Node) -> tuple[HtmlLink, ...]:
    return tuple(
        HtmlLink(
            text=_normalized_text(item),
            href=item.attrs["href"],
            title=item.attrs.get("title") or None,
            locator=SourceLocator(
                scheme="html-dom-path",
                selectors=(("dom_path", _dom_path(item)),),
            ),
        )
        for item in _walk(node)
        if item.tag == "a" and item.attrs.get("href")
    )


def _role(node: _Node, *, title_seen: bool) -> HtmlBlockRole | None:
    if node.tag == "h1" and not title_seen:
        return "title"
    if node.tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
        return "section-heading"
    if node.tag == "p":
        return "abstract" if _has_ancestor_marker(node, "abstract") else "paragraph"
    if node.tag == "li":
        return "list-item"
    if node.tag == "table":
        return "table"
    return None


def parse_html_content(
    content: bytes, *, source_content_sha256: str
) -> ParsedHtmlDocument:
    """Extract citation metadata and semantic blocks from admitted HTML bytes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "HTML bytes do not match the admitted source identity"
        )
    try:
        source = content.decode("utf-8-sig")
        builder = _TreeBuilder()
        builder.feed(source)
        builder.close()
    except (UnicodeDecodeError, ValueError) as error:
        raise DocumentParseError(
            "malformed_document", "HTML cannot be decoded or tokenized"
        ) from error
    nodes = list(_walk(builder.root))
    article = next(
        (
            node
            for node in nodes
            if node.tag == "article" and _has_ancestor(node, "main")
        ),
        None,
    )
    if article is None:
        raise DocumentParseError(
            "malformed_document", "HTML requires an article inside the main landmark"
        )

    blocks: list[ParsedHtmlBlock] = []
    heading_path: dict[int, str] = {}
    title_seen = False
    for node in _walk(article):
        if node.tag not in _BLOCK_ELEMENTS or _is_noise(node):
            continue
        if node.tag != "table" and _has_ancestor(node, "table"):
            continue
        text = _normalized_text(node)
        role = _role(node, title_seen=title_seen)
        if role is None or not text:
            continue
        if role == "title":
            title_seen = True
            section_path: tuple[str, ...] = ()
        elif role == "section-heading":
            level = int(node.tag[1])
            heading_path = {
                key: value for key, value in heading_path.items() if key < level
            }
            heading_path[level] = text
            section_path = tuple(heading_path[key] for key in sorted(heading_path))
        else:
            section_path = tuple(heading_path[key] for key in sorted(heading_path))
        blocks.append(
            ParsedHtmlBlock(
                index=len(blocks),
                role=role,
                text=text,
                source_text=_source_text(node),
                locator=SourceLocator(
                    scheme="html-dom-path",
                    selectors=(("dom_path", _dom_path(node)),),
                ),
                section_path=section_path,
                links=_links(node),
            )
        )
    if not blocks or not title_seen:
        raise DocumentParseError(
            "malformed_document", "HTML article has no semantic title and content"
        )
    return ParsedHtmlDocument(
        source_content_sha256=source_content_sha256,
        parser_name=_PARSER_NAME,
        parser_version=_PARSER_VERSION,
        metadata=_metadata(builder.root),
        blocks=tuple(blocks),
    )


__all__ = ["parse_html_content", "parser_identity"]
