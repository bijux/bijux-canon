"""Run-context helpers for critique execution."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
from typing import Any


@dataclass(frozen=True)
class CritiqueRunInput:
    """Prepared text payload used during critique execution."""

    text: str
    source_text: str

    @property
    def cache_key(self) -> str:
        """Return the stable cache key for this critique payload."""
        return hashlib.sha256(self.text.encode()).hexdigest()


def build_critique_run_input(
    context: dict[str, Any],
) -> CritiqueRunInput | None:
    """Build the critique run input from the agent context."""
    text = extract_critique_text(context)
    if text is None:
        return None
    return CritiqueRunInput(
        text=text,
        source_text=extract_source_text(context),
    )


def extract_source_text(context: dict[str, Any]) -> str:
    """Return the source text fallback chain for critique reporting."""
    return str(context.get("source_text", context.get("text", "")))


def extract_critique_text(context: dict[str, Any]) -> str | None:
    """Extract critique text from summary-oriented or direct payloads."""
    summary = context.get("summary")
    if isinstance(summary, dict):
        text_parts: list[str] = []
        for key in ["executive_summary", "key_points", "content", "text"]:
            if key not in summary:
                continue
            value = summary[key]
            if isinstance(value, str):
                text_parts.append(value)
            elif isinstance(value, list):
                text_parts.extend(item for item in value if isinstance(item, str))
        return " ".join(text_parts) if text_parts else None

    text = summary or context.get("text") or context.get("content")
    if text is None:
        text = str(context) if context else ""
    return text if isinstance(text, str) else None
