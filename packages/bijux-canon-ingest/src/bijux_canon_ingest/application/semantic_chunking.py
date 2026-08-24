# SPDX-License-Identifier: Apache-2.0
# Copyright © 2026 Bijan Mousavi

"""Structure-aware chunk formation over normalized source mappings."""

from __future__ import annotations

import re
from dataclasses import dataclass

from bijux_canon_ingest.application.source_mapping import (
    ParsedSourceDocument,
    build_chunk_span_mapping,
)
from bijux_canon_ingest.domain.document_extraction import (
    ParsedDocument,
    ParsedDocxDocument,
    ParsedHtmlDocument,
    ParsedPdfDocument,
)
from bijux_canon_ingest.domain.semantic_chunking import (
    SemanticChunk,
    SemanticChunkingPolicy,
)
from bijux_canon_ingest.domain.source_mapping import NormalizedSpanMapping


@dataclass(frozen=True, slots=True)
class _Fragment:
    mapping: NormalizedSpanMapping
    role: str
    section_path: tuple[str, ...]


_SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")
_WORD_BOUNDARY = re.compile(r"\s+")


def _boundaries(text: str, pattern: re.Pattern[str]) -> tuple[int, ...]:
    return tuple(match.end() for match in pattern.finditer(text))


def _bounded_end(
    text: str,
    *,
    start: int,
    maximum: int,
    previous_end: int,
) -> int:
    hard_end = min(start + maximum, len(text))
    if hard_end == len(text):
        return hard_end
    minimum = max(previous_end + 1, start + max(1, maximum // 2))
    for candidates in (
        _boundaries(text, _SENTENCE_BOUNDARY),
        _boundaries(text, _WORD_BOUNDARY),
    ):
        eligible = tuple(value for value in candidates if minimum <= value <= hard_end)
        if eligible:
            return eligible[-1]
    return hard_end


def _bounded_start(text: str, *, prior_start: int, end: int, overlap: int) -> int:
    if overlap == 0:
        return end
    target = max(prior_start + 1, end - overlap)
    sentence_boundaries = tuple(
        value
        for value in _boundaries(text, _SENTENCE_BOUNDARY)
        if target <= value < end
    )
    if sentence_boundaries:
        return sentence_boundaries[0]
    word_boundaries = tuple(
        value
        for value in _boundaries(text, _WORD_BOUNDARY)
        if target <= value < end
    )
    return word_boundaries[0] if word_boundaries else target


def _annotations(
    document: ParsedSourceDocument,
) -> tuple[tuple[str, tuple[str, ...]], ...]:
    if isinstance(document, ParsedPdfDocument):
        return tuple(("page", ()) for page in document.pages if page.text)
    if isinstance(document, ParsedDocument | ParsedHtmlDocument | ParsedDocxDocument):
        return tuple((block.role, block.section_path) for block in document.blocks)
    return tuple((block.role, block.section_path) for block in document.blocks)


def _fragments(
    mapping: NormalizedSpanMapping,
    *,
    role: str,
    section_path: tuple[str, ...],
    policy: SemanticChunkingPolicy,
) -> tuple[_Fragment, ...]:
    if len(mapping.normalized_text) <= policy.max_characters:
        return (_Fragment(mapping, role, section_path),)
    result: list[_Fragment] = []
    start = 0
    previous_end = -1
    while start < len(mapping.normalized_text):
        end = _bounded_end(
            mapping.normalized_text,
            start=start,
            maximum=policy.max_characters,
            previous_end=previous_end,
        )
        result.append(
            _Fragment(
                build_chunk_span_mapping(mapping, start=start, end=end),
                role,
                section_path,
            )
        )
        if end == len(mapping.normalized_text):
            break
        previous_end = end
        start = _bounded_start(
            mapping.normalized_text,
            prior_start=start,
            end=end,
            overlap=policy.overlap_characters,
        )
    return tuple(result)


def _overlap(previous: tuple[_Fragment, ...], current: tuple[_Fragment, ...]) -> int:
    overlap = 0
    for left in previous:
        for right in current:
            if (
                left.mapping.locator == right.mapping.locator
                and left.mapping.normalized_start < right.mapping.normalized_end
                and right.mapping.normalized_start < left.mapping.normalized_end
            ):
                overlap += min(
                    left.mapping.normalized_end, right.mapping.normalized_end
                ) - max(left.mapping.normalized_start, right.mapping.normalized_start)
    return overlap


def chunk_document_mappings(
    document: ParsedSourceDocument,
    mappings: tuple[NormalizedSpanMapping, ...],
    *,
    policy: SemanticChunkingPolicy | None = None,
) -> tuple[SemanticChunk, ...]:
    """Pack semantic blocks within budgets and split only oversized blocks."""

    selected_policy = policy if policy is not None else SemanticChunkingPolicy()
    annotations = _annotations(document)
    if len(mappings) != len(annotations):
        raise ValueError("document mappings must align exactly with parsed blocks")
    if any(
        mapping.source_content_sha256 != document.source_content_sha256
        for mapping in mappings
    ):
        raise ValueError("document mappings do not belong to the parsed document")

    fragments = tuple(
        fragment
        for mapping, (role, section_path) in zip(mappings, annotations, strict=True)
        for fragment in _fragments(
            mapping,
            role=role,
            section_path=section_path,
            policy=selected_policy,
        )
    )
    groups: list[tuple[_Fragment, ...]] = []
    current: list[_Fragment] = []
    current_length = 0
    separator_length = len(selected_policy.block_separator)
    for fragment in fragments:
        added_length = len(fragment.mapping.normalized_text)
        if current:
            added_length += separator_length
        if current and current_length + added_length > selected_policy.max_characters:
            groups.append(tuple(current))
            current = []
            current_length = 0
            added_length = len(fragment.mapping.normalized_text)
        current.append(fragment)
        current_length += added_length
    if current:
        groups.append(tuple(current))

    chunks: list[SemanticChunk] = []
    for index, group in enumerate(groups):
        chunks.append(
            SemanticChunk(
                source_content_sha256=document.source_content_sha256,
                chunk_index=index,
                normalized_text=selected_policy.block_separator.join(
                    fragment.mapping.normalized_text for fragment in group
                ),
                mappings=tuple(fragment.mapping for fragment in group),
                block_roles=tuple(fragment.role for fragment in group),
                section_paths=tuple(fragment.section_path for fragment in group),
                overlap_character_count=(
                    0 if index == 0 else _overlap(groups[index - 1], group)
                ),
                chunking_policy_sha256=selected_policy.policy_sha256,
                block_separator=selected_policy.block_separator,
            )
        )
    return tuple(chunks)


__all__ = ["chunk_document_mappings"]
