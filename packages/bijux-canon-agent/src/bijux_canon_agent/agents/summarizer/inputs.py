"""Input extraction helpers for the summarizer agent."""

from __future__ import annotations

from collections import Counter
import re
from typing import Any


def extract_summarizer_text(context: dict[str, Any]) -> str:
    """Extract text from direct or nested summarizer input context."""
    text = context.get("text", "")
    if not text and "file_extraction" in context:
        file_extraction = context["file_extraction"]
        if isinstance(file_extraction, dict) and "text" in file_extraction:
            text = file_extraction["text"]
    return text if isinstance(text, str) else ""


def extract_keywords(
    text: str,
    task_goal: str,
    *,
    min_keyword_length: int,
    top_keywords_count: int,
    logger: Any,
) -> list[str]:
    """Extract task- and corpus-aware keywords for summarization."""
    task_keywords = [
        word
        for word in task_goal.lower().split()
        if len(word) >= min_keyword_length
    ]
    words = re.findall(r"\b\w+\b", text.lower())
    words = [
        word for word in words if len(word) >= min_keyword_length and word.isalpha()
    ]
    word_counts = Counter(words)
    common_words = [
        word for word, _count in word_counts.most_common(top_keywords_count)
    ]
    keywords = list(dict.fromkeys(task_keywords + common_words))
    keywords = keywords[:top_keywords_count]
    logger.debug("Extracted keywords", extra={"context": {"keywords": keywords}})
    return keywords


__all__ = ["extract_keywords", "extract_summarizer_text"]
