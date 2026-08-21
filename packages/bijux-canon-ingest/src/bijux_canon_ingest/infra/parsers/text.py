# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Deterministic block extraction for admitted Markdown and plain text."""

from __future__ import annotations

import hashlib
import re

from bijux_canon_ingest.domain.document_extraction import (
    DocumentParseError,
    NewlineStyle,
    ParsedTextBlock,
    ParsedTextDocument,
    SourceLocator,
    TextBlockRole,
    TextEncoding,
)

_PARSER_VERSION = "1"
_MARKDOWN_HEADING = re.compile(r"^ {0,3}(#{1,6})(?:[ \t]+|$)")
_MARKDOWN_FENCE = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_MARKDOWN_LIST = re.compile(r"^ {0,3}(?:[-+*]|\d+[.)])[ \t]+")
_MARKDOWN_LINK = re.compile(r"\[[^\]]+\]\([^)]+\)")
_PLAIN_NUMBERED_HEADING = re.compile(
    r"^(?P<number>\d+(?:\.\d+)*\.|Appendix [A-Z]\.)\s{2,}\S"
)
_PLAIN_REFERENCE = re.compile(r"^\s{3}\[[^\]]+\]\s{2}")


def _newline_style(content: bytes) -> NewlineStyle:
    crlf = content.count(b"\r\n")
    without_crlf = content.replace(b"\r\n", b"")
    lf = without_crlf.count(b"\n")
    cr = without_crlf.count(b"\r")
    present = sum(value > 0 for value in (crlf, lf, cr))
    if present == 0:
        return "none"
    if present > 1:
        return "mixed"
    if crlf:
        return "crlf"
    if lf:
        return "lf"
    return "cr"


def _decode(content: bytes) -> tuple[str, TextEncoding, NewlineStyle]:
    encoding: TextEncoding = (
        "utf-8-sig" if content.startswith(b"\xef\xbb\xbf") else "utf-8"
    )
    try:
        source = content.decode("utf-8-sig")
    except UnicodeDecodeError as error:
        raise DocumentParseError(
            "malformed_document", "text source is not valid UTF-8"
        ) from error
    normalized = source.replace("\r\n", "\n").replace("\r", "\n")
    if not normalized.strip():
        raise DocumentParseError("malformed_document", "text source has no content")
    return normalized, encoding, _newline_style(content)


def _line_offsets(lines: list[str]) -> list[int]:
    offsets: list[int] = []
    position = 0
    for line in lines:
        offsets.append(position)
        position += len(line) + 1
    return offsets


def _add_block(
    blocks: list[ParsedTextBlock],
    *,
    normalized: str,
    normalized_sha256: str,
    lines: list[str],
    offsets: list[int],
    line_start: int,
    line_end: int,
    role: TextBlockRole,
    scheme: str,
    section_path: tuple[str, ...],
) -> None:
    char_start = offsets[line_start]
    char_end = offsets[line_end] + len(lines[line_end])
    text = normalized[char_start:char_end]
    if not text:
        return
    blocks.append(
        ParsedTextBlock(
            index=len(blocks),
            role=role,
            text=text,
            locator=SourceLocator(
                scheme=scheme,
                selectors=(
                    ("line_start", line_start + 1),
                    ("line_end", line_end + 1),
                    ("char_start", char_start),
                    ("char_end", char_end),
                    ("normalized_text_sha256", normalized_sha256),
                ),
            ),
            section_path=section_path,
        )
    )


def _markdown_is_table_row(line: str) -> bool:
    stripped = line.strip()
    return (
        stripped.startswith("|") and stripped.endswith("|") and stripped.count("|") >= 2
    )


def _markdown_is_comment(line: str) -> bool:
    return line.lstrip().startswith("<!--")


def _markdown_is_starter(line: str) -> bool:
    return bool(
        _MARKDOWN_HEADING.match(line)
        or _MARKDOWN_FENCE.match(line)
        or _MARKDOWN_LIST.match(line)
        or line.lstrip().startswith(">")
        or _markdown_is_table_row(line)
        or _markdown_is_comment(line)
    )


def _heading_label(line: str) -> tuple[int, str]:
    match = _MARKDOWN_HEADING.match(line)
    assert match is not None
    level = len(match.group(1))
    return level, line[match.end() :].strip().rstrip("#").rstrip()


def _markdown_blocks(
    normalized: str,
    lines: list[str],
    offsets: list[int],
) -> tuple[ParsedTextBlock, ...]:
    blocks: list[ParsedTextBlock] = []
    normalized_sha256 = hashlib.sha256(normalized.encode()).hexdigest()
    headings: dict[int, str] = {}
    section_path: tuple[str, ...] = ()
    index = 0

    if lines and lines[0] == "---":
        front_matter_end = next(
            (item for item in range(1, len(lines)) if lines[item] == "---"), None
        )
        if front_matter_end is None:
            raise DocumentParseError(
                "malformed_document", "Markdown front matter is not terminated"
            )
        _add_block(
            blocks,
            normalized=normalized,
            normalized_sha256=normalized_sha256,
            lines=lines,
            offsets=offsets,
            line_start=0,
            line_end=front_matter_end,
            role="front-matter",
            scheme="markdown-line-span",
            section_path=(),
        )
        index = front_matter_end + 1

    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        line = lines[index]
        fence = _MARKDOWN_FENCE.match(line)
        if fence is not None:
            marker = fence.group(1)
            end = index + 1
            fence_closing = re.compile(
                rf"^ {{0,3}}{re.escape(marker[0])}{{{len(marker)},}}\s*$"
            )
            while end < len(lines) and fence_closing.match(lines[end]) is None:
                end += 1
            if end == len(lines):
                raise DocumentParseError(
                    "malformed_document", "Markdown fenced code block is not terminated"
                )
            _add_block(
                blocks,
                normalized=normalized,
                normalized_sha256=normalized_sha256,
                lines=lines,
                offsets=offsets,
                line_start=index,
                line_end=end,
                role="code-block",
                scheme="markdown-line-span",
                section_path=section_path,
            )
            index = end + 1
            continue
        if _MARKDOWN_HEADING.match(line):
            level, label = _heading_label(line)
            headings = {key: value for key, value in headings.items() if key < level}
            headings[level] = label
            section_path = tuple(headings[key] for key in sorted(headings))
            _add_block(
                blocks,
                normalized=normalized,
                normalized_sha256=normalized_sha256,
                lines=lines,
                offsets=offsets,
                line_start=index,
                line_end=index,
                role="heading",
                scheme="markdown-line-span",
                section_path=section_path,
            )
            index += 1
            continue
        if _markdown_is_table_row(line):
            _add_block(
                blocks,
                normalized=normalized,
                normalized_sha256=normalized_sha256,
                lines=lines,
                offsets=offsets,
                line_start=index,
                line_end=index,
                role="table-row",
                scheme="markdown-line-span",
                section_path=section_path,
            )
            index += 1
            continue
        if _markdown_is_comment(line):
            end = index
            while end < len(lines) and "-->" not in lines[end]:
                end += 1
            if end == len(lines):
                raise DocumentParseError(
                    "malformed_document", "Markdown comment is not terminated"
                )
            _add_block(
                blocks,
                normalized=normalized,
                normalized_sha256=normalized_sha256,
                lines=lines,
                offsets=offsets,
                line_start=index,
                line_end=end,
                role="comment",
                scheme="markdown-line-span",
                section_path=section_path,
            )
            index = end + 1
            continue
        if line.lstrip().startswith(">"):
            quote_end = index
            while quote_end + 1 < len(lines) and lines[
                quote_end + 1
            ].lstrip().startswith(">"):
                quote_end += 1
            segment_start = index
            while segment_start <= quote_end:
                segment_end = segment_start
                content = lines[segment_start].lstrip()[1:].strip()
                if not (content.startswith("[!") and content.endswith("]")):
                    while segment_end < quote_end and not lines[
                        segment_end
                    ].rstrip().endswith((".", "?", "!")):
                        segment_end += 1
                segment_text = "\n".join(lines[segment_start : segment_end + 1])
                role: TextBlockRole = (
                    "link" if _MARKDOWN_LINK.search(segment_text) else "block-quote"
                )
                _add_block(
                    blocks,
                    normalized=normalized,
                    normalized_sha256=normalized_sha256,
                    lines=lines,
                    offsets=offsets,
                    line_start=segment_start,
                    line_end=segment_end,
                    role=role,
                    scheme="markdown-line-span",
                    section_path=section_path,
                )
                segment_start = segment_end + 1
            index = quote_end + 1
            continue
        if _MARKDOWN_LIST.match(line):
            end = index
            while end + 1 < len(lines):
                candidate = lines[end + 1]
                if (
                    not candidate.strip()
                    or _MARKDOWN_LIST.match(candidate)
                    or _markdown_is_starter(candidate)
                ):
                    break
                if candidate.startswith((" ", "\t")):
                    end += 1
                    continue
                break
            _add_block(
                blocks,
                normalized=normalized,
                normalized_sha256=normalized_sha256,
                lines=lines,
                offsets=offsets,
                line_start=index,
                line_end=end,
                role="list-item",
                scheme="markdown-line-span",
                section_path=section_path,
            )
            index = end + 1
            continue
        end = index
        while end + 1 < len(lines):
            candidate = lines[end + 1]
            if not candidate.strip() or _markdown_is_starter(candidate):
                break
            end += 1
        _add_block(
            blocks,
            normalized=normalized,
            normalized_sha256=normalized_sha256,
            lines=lines,
            offsets=offsets,
            line_start=index,
            line_end=end,
            role="paragraph",
            scheme="markdown-line-span",
            section_path=section_path,
        )
        index = end + 1
    return tuple(blocks)


def _plain_is_heading(lines: list[str], index: int, *, title_index: int | None) -> bool:
    if index == title_index or lines[index] != lines[index].lstrip():
        return False
    stripped = lines[index].strip()
    if not stripped or len(stripped) > 120:
        return False
    if _PLAIN_NUMBERED_HEADING.match(lines[index]):
        return True
    before_blank = index == 0 or not lines[index - 1].strip()
    after_blank = index + 1 == len(lines) or not lines[index + 1].strip()
    return before_blank and after_blank and not stripped.endswith((".", ":"))


def _plain_blocks(
    normalized: str,
    lines: list[str],
    offsets: list[int],
) -> tuple[ParsedTextBlock, ...]:
    blocks: list[ParsedTextBlock] = []
    normalized_sha256 = hashlib.sha256(normalized.encode()).hexdigest()
    toc_start = next(
        (
            index
            for index, line in enumerate(lines)
            if line.strip() == "Table of Contents"
        ),
        None,
    )
    main_start = next(
        (
            index
            for index, line in enumerate(lines)
            if index > (toc_start or 0) and _PLAIN_NUMBERED_HEADING.match(line)
        ),
        None,
    )
    title_index = next(
        (
            index
            for index, line in enumerate(lines[: main_start or len(lines)])
            if len(line) - len(line.lstrip()) >= 10
            and line.strip()
            and (index == 0 or not lines[index - 1].strip())
            and (index + 1 == len(lines) or not lines[index + 1].strip())
        ),
        None,
    )
    section_path: tuple[str, ...] = ()
    in_syntax_appendix = False
    index = 0
    while index < len(lines):
        if not lines[index].strip():
            index += 1
            continue
        line = lines[index]
        if index == title_index:
            role: TextBlockRole = "title"
            end = index
        elif toc_start is not None and index == toc_start:
            role = "section-heading"
            end = index
            section_path = (line.strip(),)
        elif (
            toc_start is not None
            and main_start is not None
            and toc_start < index < main_start
        ):
            role = "list-item"
            end = index
        elif _plain_is_heading(lines, index, title_index=title_index):
            role = "section-heading"
            end = index
            section_path = (line.strip(),)
            if line.startswith("Appendix A.  Collected ABNF"):
                in_syntax_appendix = True
            elif line.startswith("Appendix B."):
                in_syntax_appendix = False
        elif in_syntax_appendix and " = " in line:
            role = "syntax-example"
            end = index
        elif _PLAIN_REFERENCE.match(line):
            role = "reference"
            end = index
            while end + 1 < len(lines) and lines[end + 1].strip():
                if _PLAIN_REFERENCE.match(lines[end + 1]):
                    break
                end += 1
        else:
            role = "paragraph"
            end = index
            while end + 1 < len(lines) and lines[end + 1].strip():
                candidate = end + 1
                if (
                    _plain_is_heading(lines, candidate, title_index=title_index)
                    or _PLAIN_REFERENCE.match(lines[candidate])
                    or (in_syntax_appendix and " = " in lines[candidate])
                ):
                    break
                end += 1
        _add_block(
            blocks,
            normalized=normalized,
            normalized_sha256=normalized_sha256,
            lines=lines,
            offsets=offsets,
            line_start=index,
            line_end=end,
            role=role,
            scheme="text-line-span",
            section_path=section_path,
        )
        index = end + 1
    return tuple(blocks)


def parse_markdown_content(
    content: bytes, *, source_content_sha256: str
) -> ParsedTextDocument:
    """Extract exact semantic blocks from admitted Markdown bytes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "Markdown bytes do not match the admitted source identity"
        )
    normalized, encoding, newline_style = _decode(content)
    lines = normalized.split("\n")
    offsets = _line_offsets(lines)
    return ParsedTextDocument(
        format_id="markdown",
        source_content_sha256=source_content_sha256,
        parser_name="bijux-canon-ingest-markdown",
        parser_version=_PARSER_VERSION,
        encoding=encoding,
        newline_style=newline_style,
        normalized_text=normalized,
        blocks=_markdown_blocks(normalized, lines, offsets),
    )


def parse_text_content(
    content: bytes, *, source_content_sha256: str
) -> ParsedTextDocument:
    """Extract exact semantic blocks from admitted plain-text bytes."""

    if hashlib.sha256(content).hexdigest() != source_content_sha256:
        raise DocumentParseError(
            "source_changed", "text bytes do not match the admitted source identity"
        )
    normalized, encoding, newline_style = _decode(content)
    lines = normalized.split("\n")
    offsets = _line_offsets(lines)
    return ParsedTextDocument(
        format_id="text",
        source_content_sha256=source_content_sha256,
        parser_name="bijux-canon-ingest-text",
        parser_version=_PARSER_VERSION,
        encoding=encoding,
        newline_style=newline_style,
        normalized_text=normalized,
        blocks=_plain_blocks(normalized, lines, offsets),
    )


__all__ = ["parse_markdown_content", "parse_text_content"]
