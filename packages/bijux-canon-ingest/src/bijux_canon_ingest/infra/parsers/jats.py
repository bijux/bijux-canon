# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic semantic extraction from admitted JATS article XML."""

from __future__ import annotations

import hashlib
import re
import xml.etree.ElementTree as ET
from collections.abc import Iterable

from bijux_canon_ingest.domain.document_extraction import (
    BlockRole,
    DocumentMetadata,
    DocumentParseError,
    ParsedBlock,
    ParsedDocument,
    SourceLocator,
)

_PARSER_NAME = "bijux-canon-ingest-jats"
_PARSER_VERSION = "1"
_XML_LANG = "{http://www.w3.org/XML/1998/namespace}lang"
_XLINK_HREF = "{http://www.w3.org/1999/xlink}href"
_ENTITY_DECLARATION = re.compile(rb"<!ENTITY\s", re.IGNORECASE)
_EXCLUDED_PARAGRAPH_ANCESTORS = frozenset(
    {"caption", "fig", "ref", "ref-list", "table", "table-wrap"}
)


def _local_name(element: ET.Element) -> str:
    return element.tag.rsplit("}", 1)[-1]


def _children(element: ET.Element, name: str) -> Iterable[ET.Element]:
    return (child for child in element if _local_name(child) == name)


def _first_descendant(element: ET.Element, name: str) -> ET.Element | None:
    return next((item for item in element.iter() if _local_name(item) == name), None)


def _normalized_text(element: ET.Element | None) -> str:
    if element is None:
        return ""
    return " ".join(" ".join(element.itertext()).split())


def _source_text(element: ET.Element) -> str:
    return "".join(element.itertext())


def _parent_map(root: ET.Element) -> dict[ET.Element, ET.Element]:
    return {child: parent for parent in root.iter() for child in parent}


def _element_path(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> str:
    parts: list[str] = []
    current = element
    while True:
        name = _local_name(current)
        parent = parents.get(current)
        if parent is None:
            index = 1
        else:
            siblings = [child for child in parent if _local_name(child) == name]
            index = siblings.index(current) + 1
        parts.append(f"{name}[{index}]")
        if parent is None:
            break
        current = parent
    return "/" + "/".join(reversed(parts))


def _ancestors(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[ET.Element, ...]:
    values: list[ET.Element] = []
    current = parents.get(element)
    while current is not None:
        values.append(current)
        current = parents.get(current)
    return tuple(reversed(values))


def _section_path(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> tuple[str, ...]:
    sections = [
        item for item in _ancestors(element, parents) if _local_name(item) == "sec"
    ]
    headings = (
        _normalized_text(next(iter(_children(section, "title")), None))
        for section in sections
    )
    return tuple(heading for heading in headings if heading)


def _author_name(contributor: ET.Element) -> str:
    name = next(iter(_children(contributor, "name")), None)
    if name is not None:
        given = _normalized_text(_first_descendant(name, "given-names"))
        surname = _normalized_text(_first_descendant(name, "surname"))
        return " ".join(value for value in (given, surname) if value)
    return _normalized_text(_first_descendant(contributor, "collab"))


def _publication_year(article_meta: ET.Element) -> int | None:
    dates = [item for item in article_meta if _local_name(item) == "pub-date"]
    for preferred_type in ("epub", "electronic", "ppub", "print", "collection"):
        for date in dates:
            if (
                date.get("pub-type") == preferred_type
                or date.get("date-type") == preferred_type
            ):
                year = _normalized_text(_first_descendant(date, "year"))
                if year.isdigit():
                    return int(year)
    for date in dates:
        year = _normalized_text(_first_descendant(date, "year"))
        if year.isdigit():
            return int(year)
    return None


def _metadata(root: ET.Element) -> DocumentMetadata:
    article_meta = _first_descendant(root, "article-meta")
    if article_meta is None:
        raise DocumentParseError(
            "missing_required_metadata", "JATS article has no article-meta element"
        )
    title = _normalized_text(_first_descendant(article_meta, "article-title"))
    journal = _normalized_text(_first_descendant(root, "journal-title"))
    doi = next(
        (
            _normalized_text(item)
            for item in article_meta.iter()
            if _local_name(item) == "article-id" and item.get("pub-id-type") == "doi"
        ),
        "",
    )
    authors = tuple(
        author
        for item in article_meta.iter()
        if _local_name(item) == "contrib" and item.get("contrib-type") == "author"
        if (author := _author_name(item))
    )
    year = _publication_year(article_meta)
    license_element = _first_descendant(article_meta, "license")
    license_text = _normalized_text(license_element)
    license_url = None if license_element is None else license_element.get(_XLINK_HREF)
    missing = [
        name
        for name, value in (
            ("title", title),
            ("authors", authors),
            ("doi", doi),
            ("journal", journal),
            ("publication_year", year),
            ("license", license_text),
        )
        if not value
    ]
    if missing:
        raise DocumentParseError(
            "missing_required_metadata",
            f"JATS article is missing required metadata: {', '.join(missing)}",
        )
    assert year is not None
    return DocumentMetadata(
        title=title,
        authors=authors,
        doi=doi,
        journal=journal,
        publication_year=year,
        license_text=license_text,
        license_url=license_url,
        language=root.get(_XML_LANG),
    )


def _role(
    element: ET.Element,
    parents: dict[ET.Element, ET.Element],
) -> BlockRole | None:
    name = _local_name(element)
    ancestor_names = {_local_name(item) for item in _ancestors(element, parents)}
    parent = parents.get(element)
    if name == "article-title" and "article-meta" in ancestor_names:
        return "title"
    if name == "p" and "abstract" in ancestor_names:
        return "abstract"
    if name == "title" and parent is not None and _local_name(parent) == "sec":
        return "section-heading"
    if (
        name == "p"
        and "body" in ancestor_names
        and not ancestor_names.intersection(_EXCLUDED_PARAGRAPH_ANCESTORS)
    ):
        return "paragraph"
    if name == "caption" and "body" in ancestor_names:
        return "caption"
    if name == "table-wrap" and "body" in ancestor_names:
        return "table"
    if name == "ref" and "ref-list" in ancestor_names:
        return "reference"
    return None


def parse_jats_content(content: bytes, *, source_content_sha256: str) -> ParsedDocument:
    """Extract metadata and ordered blocks from already-admitted JATS bytes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "JATS bytes do not match the admitted source identity"
        )
    if _ENTITY_DECLARATION.search(content):
        raise DocumentParseError(
            "unsafe_markup", "JATS entity declarations are forbidden"
        )
    try:
        root = ET.fromstring(content)
    except ET.ParseError as error:
        raise DocumentParseError(
            "malformed_document", "JATS XML is malformed"
        ) from error
    if _local_name(root) != "article":
        raise DocumentParseError("format_mismatch", "XML root element is not article")

    parents = _parent_map(root)
    blocks: list[ParsedBlock] = []
    for element in root.iter():
        role = _role(element, parents)
        text = _normalized_text(element)
        if role is None or not text:
            continue
        blocks.append(
            ParsedBlock(
                index=len(blocks),
                role=role,
                text=text,
                source_text=_source_text(element),
                locator=SourceLocator(
                    scheme="jats-element-path",
                    selectors=(("element_path", _element_path(element, parents)),),
                ),
                section_path=_section_path(element, parents),
            )
        )
    return ParsedDocument(
        format_id="jats",
        source_content_sha256=source_content_sha256,
        parser_name=_PARSER_NAME,
        parser_version=_PARSER_VERSION,
        metadata=_metadata(root),
        blocks=tuple(blocks),
    )


__all__ = ["parse_jats_content"]
