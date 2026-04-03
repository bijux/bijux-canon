"""Post-processing helpers for structured summaries."""

from __future__ import annotations

from collections import Counter
from typing import Any


def combine_summaries(
    agent: Any, extractive_summary: str, abstractive_summary: str
) -> str:
    """Mix extractive and abstractive sentences based on configured weights."""
    if not extractive_summary and not abstractive_summary:
        return ""
    if not extractive_summary:
        return abstractive_summary
    if not abstractive_summary:
        return extractive_summary

    extractive_weight = agent.strategy_weights.get(agent.STRATEGY_EXTRACTIVE, 0.6)
    abstractive_weight = agent.strategy_weights.get(agent.STRATEGY_ABSTRACTIVE, 0.4)

    extractive_sentences = [s.strip() for s in extractive_summary.split(".")]
    abstractive_sentences = [s.strip() for s in abstractive_summary.split(".")]
    extractive_sentences = [s for s in extractive_sentences if s]
    abstractive_sentences = [s for s in abstractive_sentences if s]

    summary_sentences: list[str] = []
    current_length = 0
    extractive_idx, abstractive_idx = 0, 0
    total_sentences = len(extractive_sentences) + len(abstractive_sentences)
    if total_sentences == 0:
        return ""

    target_extractive = int(total_sentences * extractive_weight)
    target_abstractive = int(total_sentences * abstractive_weight)

    while (
        extractive_idx < len(extractive_sentences)
        or abstractive_idx < len(abstractive_sentences)
    ) and current_length < agent.max_length:
        if extractive_idx < len(extractive_sentences) and (
            extractive_idx < target_extractive
            or abstractive_idx >= len(abstractive_sentences)
        ):
            sentence = extractive_sentences[extractive_idx]
            extractive_idx += 1
        elif abstractive_idx < len(abstractive_sentences) and (
            abstractive_idx < target_abstractive
            or extractive_idx >= len(extractive_sentences)
        ):
            sentence = abstractive_sentences[abstractive_idx]
            abstractive_idx += 1
        else:
            if extractive_idx < len(extractive_sentences):
                sentence = extractive_sentences[extractive_idx]
                extractive_idx += 1
            else:
                sentence = abstractive_sentences[abstractive_idx]
                abstractive_idx += 1

        sentence_length = len(sentence)
        if current_length + sentence_length > agent.max_length:
            break
        summary_sentences.append(sentence)
        current_length += sentence_length

    summary = ". ".join(summary_sentences)
    if summary:
        summary += "."
    agent.logger.debug(
        "Combined extractive and abstractive summaries",
        extra={
            "context": {
                "extractive_sentences": extractive_idx,
                "abstractive_sentences": abstractive_idx,
                "summary_length": len(summary),
                "extractive_weight": extractive_weight,
                "abstractive_weight": abstractive_weight,
            }
        },
    )
    return summary


def format_structured_summary(
    agent: Any, summary_text: str, original_text: str, keywords: list[str]
) -> dict[str, Any]:
    """Turn raw summary text into structured sections."""
    if not summary_text:
        return {
            "executive_summary": "No summary generated.",
            "key_points": ["- No key points available."],
            "actionable_insights": "N/A",
            "critical_risks": "Unable to assess risks due to lack of summary.",
            "missing_info": "Summary generation failed.",
        }

    sentences = [s.strip() for s in summary_text.split(".")]
    sentences = [s for s in sentences if s]

    scored_sentences: list[tuple[str, float]] = []
    for idx, sentence in enumerate(sentences):
        score = sum(1 for kw in keywords if kw.lower() in sentence.lower())
        positional_factor = 1.0 / (idx + 1) * 0.5
        score += positional_factor
        scored_sentences.append((sentence, score))
    scored_sentences.sort(key=lambda x: x[1], reverse=True)

    executive_summary_sentences = [s[0] for s in scored_sentences[:2]]
    executive_summary = ". ".join(executive_summary_sentences)
    if executive_summary:
        executive_summary += "."

    key_points = [
        f"- {sentence}"
        for sentence in sentences
        if any(kw in sentence.lower() for kw in keywords)
    ]
    key_points = list(dict.fromkeys(key_points))[:5]
    if not key_points:
        key_points = ["- No specific key points identified."]

    actionable_insights = "No actionable insights identified."
    for sentence in sentences:
        if any(
            word in sentence.lower()
            for word in ["should", "recommend", "suggest", "monitor", "invest"]
        ):
            actionable_insights = sentence
            break

    critical_risks = "No critical risks identified."
    if len(summary_text) < 50:
        critical_risks = "Summary may be too short to capture key details."
    elif len(summary_text) > agent.max_length * 0.9:
        critical_risks = "Summary may be too long and include unnecessary details."

    char_counts = Counter(original_text)
    repeated_chars = [char for char, count in char_counts.items() if count > 10]
    if repeated_chars:
        critical_risks = (
            "Possible OCR errors (e.g., repeated characters: "
            f"{', '.join(repeated_chars)}) may lead to incomplete insights."
        )

    missing_keywords = [
        kw
        for kw in keywords
        if not any(kw.lower() in point.lower() for point in key_points)
    ]
    missing_info = (
        f"Missing details related to: {', '.join(missing_keywords)}."
        if missing_keywords
        else "No missing information noted."
    )

    structured_summary = {
        "executive_summary": executive_summary,
        "key_points": key_points,
        "actionable_insights": actionable_insights,
        "critical_risks": critical_risks,
        "missing_info": missing_info,
    }

    agent.logger.debug(
        "Formatted structured summary",
        extra={
            "context": {
                "structured_fields": list(structured_summary.keys()),
                "executive_summary_length": len(executive_summary),
                "key_points_count": len(key_points),
                "missing_info": missing_info,
            }
        },
    )
    return structured_summary
