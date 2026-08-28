# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic semantic extraction from admitted DOCX packages."""

from __future__ import annotations

import hashlib
import io
import xml.etree.ElementTree as ET
import zipfile

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    DocxBlockRole,
    DocxDocumentMetadata,
    ParsedDocxBlock,
    ParsedDocxDocument,
    SourceLocator,
)

_W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"
_R = "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}"
_REL = "{http://schemas.openxmlformats.org/package/2006/relationships}"
_PARSER_NAME = "bijux-canon-ingest-docx"
_PARSER_VERSION = "1"


def parser_identity() -> tuple[str, str, str]:
    """Return the extraction contract that governs DOCX reuse."""

    return _PARSER_NAME, _PARSER_VERSION, "bijux.canon.ingest.parsed_docx_document.v1"


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1]


def _xml(content: bytes, *, part: str) -> ET.Element:
    if b"<!ENTITY" in content.upper():
        raise DocumentParseError("unsafe_markup", f"DOCX part {part} declares entities")
    try:
        return ET.fromstring(content)
    except ET.ParseError as error:
        raise DocumentParseError(
            "malformed_document", f"DOCX part {part} is malformed"
        ) from error


def _text(element: ET.Element) -> str:
    return " ".join(
        " ".join(item.text or "" for item in element.iter(f"{_W}t")).split()
    )


def _metadata(core: ET.Element | None) -> DocxDocumentMetadata:
    fields = (
        ()
        if core is None
        else tuple(
            (_local_name(child.tag), child.text or "") for child in core if child.text
        )
    )
    values = dict(fields)
    return DocxDocumentMetadata(
        creator=values.get("creator"),
        last_modified_by=values.get("lastModifiedBy"),
        created_at=values.get("created"),
        modified_at=values.get("modified"),
        revision=values.get("revision"),
        raw_fields=fields,
    )


def _relationships(root: ET.Element | None) -> dict[str, str]:
    if root is None:
        return {}
    return {
        item.get("Id", ""): item.get("Target", "")
        for item in root.findall(f"{_REL}Relationship")
        if item.get("Id") and item.get("Target")
    }


def _style(element: ET.Element) -> str:
    style = element.find(f".//{_W}pStyle")
    return "" if style is None else style.get(f"{_W}val", "")


def _locator(
    *,
    package_part: str,
    block_index: int,
    block_kind: str,
    extra: tuple[tuple[str, str | int], ...] = (),
) -> SourceLocator:
    return SourceLocator(
        scheme="ooxml-package-part-and-block-index",
        selectors=(
            ("package_part", package_part),
            ("block_index", block_index),
            ("block_kind", block_kind),
            *extra,
        ),
    )


def _append(
    blocks: list[ParsedDocxBlock],
    *,
    role: DocxBlockRole,
    text: str,
    locator: SourceLocator,
    section_path: tuple[str, ...],
    target: str | None = None,
) -> None:
    if text:
        blocks.append(
            ParsedDocxBlock(
                index=len(blocks),
                role=role,
                text=text,
                locator=locator,
                section_path=section_path,
                target=target,
            )
        )


def _hyperlinks(
    blocks: list[ParsedDocxBlock],
    element: ET.Element,
    *,
    block_index: int,
    block_kind: str,
    relationships: dict[str, str],
    section_path: tuple[str, ...],
) -> None:
    for hyperlink_index, hyperlink in enumerate(element.iter(f"{_W}hyperlink"), 1):
        relationship_id = hyperlink.get(f"{_R}id")
        anchor = hyperlink.get(f"{_W}anchor")
        target = relationships.get(relationship_id or "")
        if target is None and anchor:
            target = f"#{anchor}"
        _append(
            blocks,
            role="hyperlink",
            text=_text(hyperlink),
            locator=_locator(
                package_part="word/document.xml",
                block_index=block_index,
                block_kind=block_kind,
                extra=(("hyperlink_index", hyperlink_index),),
            ),
            section_path=section_path,
            target=target,
        )


def parse_docx_content(
    content: bytes, *, source_content_sha256: str
) -> ParsedDocxDocument:
    """Extract properties, body structure, links, tables, and footnotes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "DOCX bytes do not match the admitted source identity"
        )
    try:
        archive = zipfile.ZipFile(io.BytesIO(content))
    except (OSError, zipfile.BadZipFile, zipfile.LargeZipFile) as error:
        raise DocumentParseError(
            "malformed_document", "DOCX ZIP is malformed"
        ) from error
    try:
        with archive:
            document = _xml(archive.read("word/document.xml"), part="word/document.xml")
            core = (
                _xml(archive.read("docProps/core.xml"), part="docProps/core.xml")
                if "docProps/core.xml" in archive.namelist()
                else None
            )
            relationships = (
                _xml(
                    archive.read("word/_rels/document.xml.rels"),
                    part="word/_rels/document.xml.rels",
                )
                if "word/_rels/document.xml.rels" in archive.namelist()
                else None
            )
            footnotes = (
                _xml(archive.read("word/footnotes.xml"), part="word/footnotes.xml")
                if "word/footnotes.xml" in archive.namelist()
                else None
            )
    except (KeyError, OSError, RuntimeError, zipfile.BadZipFile) as error:
        raise DocumentParseError(
            "malformed_document", "DOCX required package parts cannot be read"
        ) from error

    body = document.find(f"{_W}body")
    if body is None:
        raise DocumentParseError("malformed_document", "DOCX has no document body")
    body_children = list(body)
    first_heading = next(
        (
            index
            for index, child in enumerate(body_children)
            if _style(child).lower().startswith("heading")
        ),
        len(body_children),
    )
    title_candidates = [
        (index, _text(child))
        for index, child in enumerate(body_children[:first_heading])
        if _local_name(child.tag) == "p" and _text(child)
    ]
    title_index = title_candidates[-1][0] if title_candidates else -1
    relationship_targets = _relationships(relationships)
    blocks: list[ParsedDocxBlock] = []
    section_path: tuple[str, ...] = ()
    for zero_index, child in enumerate(body_children):
        block_index = zero_index + 1
        kind = _local_name(child.tag)
        text = _text(child)
        if kind == "p" and text:
            style = _style(child)
            if zero_index == title_index:
                role: DocxBlockRole = "title"
            elif style.lower().startswith("heading"):
                role = "heading"
                section_path = (text,)
            elif child.find(f".//{_W}numPr") is not None:
                role = "list-item"
            else:
                role = "paragraph"
            _append(
                blocks,
                role=role,
                text=text,
                locator=_locator(
                    package_part="word/document.xml",
                    block_index=block_index,
                    block_kind=kind,
                ),
                section_path=section_path,
            )
        elif kind == "tbl":
            for cell_index, cell in enumerate(child.iter(f"{_W}tc"), 1):
                _append(
                    blocks,
                    role="table-cell",
                    text=_text(cell),
                    locator=_locator(
                        package_part="word/document.xml",
                        block_index=block_index,
                        block_kind=kind,
                        extra=(("table_cell_index", cell_index),),
                    ),
                    section_path=section_path,
                )
        elif kind == "sdt" and text:
            _append(
                blocks,
                role="paragraph",
                text=text,
                locator=_locator(
                    package_part="word/document.xml",
                    block_index=block_index,
                    block_kind=kind,
                ),
                section_path=section_path,
            )
        _hyperlinks(
            blocks,
            child,
            block_index=block_index,
            block_kind=kind,
            relationships=relationship_targets,
            section_path=section_path,
        )
    if footnotes is not None:
        for footnote in footnotes.findall(f"{_W}footnote"):
            identifier = int(footnote.get(f"{_W}id", "-1"))
            if identifier >= 0:
                _append(
                    blocks,
                    role="footnote",
                    text=_text(footnote),
                    locator=_locator(
                        package_part="word/footnotes.xml",
                        block_index=identifier,
                        block_kind="footnote",
                    ),
                    section_path=(),
                )
    return ParsedDocxDocument(
        source_content_sha256=source_content_sha256,
        parser_name=_PARSER_NAME,
        parser_version=_PARSER_VERSION,
        metadata=_metadata(core),
        blocks=tuple(blocks),
    )


__all__ = ["parse_docx_content", "parser_identity"]
