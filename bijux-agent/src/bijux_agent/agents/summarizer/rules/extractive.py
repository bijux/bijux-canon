"""Extractive summarization helpers."""

from __future__ import annotations

import re
from typing import Any


def parse_sections(agent: Any, text: str, keywords: list[str]) -> list[dict[str, Any]]:
    """Parse text headings and sort by keyword relevance."""
    section_pattern = (
        r"(?m)^(?:\d+\.\s+|[A-Z][A-Za-z\s]+(?=\n\s*\n))"
        r"(?=.*?(?=\n\d+\.\s+|\n[A-Z][A-Za-z\s]+(?=\n\s*\n)|\Z))"
    )
    sections_raw = re.split(section_pattern, text)
    section_headings = re.findall(
        r"^(?:\d+\.\s+.*|[A-Z][A-Za-z\s]+(?=\n\s*\n))",
        text,
        re.MULTILINE,
    )

    sections: list[dict[str, Any]] = []
    for i, heading in enumerate(section_headings):
        content = sections_raw[i + 1].strip() if i + 1 < len(sections_raw) else ""
        relevance_score = sum(
            1
            for kw in keywords
            if kw.lower() in heading.lower() or kw.lower() in content.lower()
        )
        sections.append(
            {
                "heading": heading.strip(),
                "content": content,
                "relevance_score": relevance_score,
            }
        )

    sections.sort(key=lambda x: x["relevance_score"], reverse=True)
    if not sections:
        sections.append(
            {
                "heading": "Full Text",
                "content": text,
                "relevance_score": 1.0,
            }
        )

    return sections


def generate_extractive_summary(
    agent: Any, sections: list[dict[str, Any]], keywords: list[str]
) -> str:
    """Select sentences that align best with keywords and section relevance."""
    keyword_weights = {kw.lower(): 1.0 for kw in keywords}
    for kw in list(keyword_weights):
        section_count = sum(
            1
            for section in sections
            if kw in section["content"].lower() or kw in section["heading"].lower()
        )
        if section_count > 1:
            keyword_weights[kw] += section_count * 0.5

    scored_sentences: list[tuple[str, float]] = []
    for section in sections:
        section_text = f"{section['heading']}. {section['content']}"
        sentences = [s.strip() for s in section_text.replace("\n", " ").split(".")]
        sentences = [s for s in sentences if s]

        for idx, sentence in enumerate(sentences):
            score = 0.0
            sentence_lower = sentence.lower()
            for kw, weight in keyword_weights.items():
                if kw in sentence_lower:
                    score += weight
            score += section["relevance_score"] * 0.5
            positional_factor = 1.0 / (idx + 1) * 0.5
            score += positional_factor
            score += len(sentence) / 100
            scored_sentences.append((sentence, score))

    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    summary_sentences: list[str] = []
    current_length = 0
    for sentence, _ in scored_sentences:
        sentence_length = len(sentence)
        if current_length + sentence_length > agent.max_length:
            break
        summary_sentences.append(sentence)
        current_length += sentence_length

    summary = ". ".join(summary_sentences)
    if summary:
        summary += "."
    agent.logger.debug(
        "Extractive summary generated",
        extra={
            "context": {
                "num_sentences": len(summary_sentences),
                "summary_length": len(summary),
                "keywords": list(keyword_weights.keys()),
            }
        },
    )
    return summary
