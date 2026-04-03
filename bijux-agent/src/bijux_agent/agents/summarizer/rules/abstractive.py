"""Abstractive summarization helpers using LLM backends."""

from __future__ import annotations

from typing import Any

from bijux_agent.utilities.logger_manager import MetricType


async def generate_abstractive_summary(
    agent: Any,
    sections: list[dict[str, Any]],
    prompt_prefix: str,
    task_goal: str,
    keywords: list[str],
) -> str:
    """Compose an abstractive summary using LLM-generated chunks."""
    if not agent.llm:
        raise ValueError("LLM backend not initialized for abstractive summarization")

    section_texts = [
        f"{section['heading']}\n{section['content']}" for section in sections
    ]
    combined_text = "\n\n".join(section_texts)
    if len(combined_text) <= agent.chunk_size:
        chunks = [combined_text]
    else:
        chunks = [
            combined_text[i : i + agent.chunk_size]
            for i in range(0, len(combined_text), agent.chunk_size)
        ]
    agent.logger.debug(
        f"Split text into {len(chunks)} chunks for abstractive summarization",
        extra={"context": {"chunk_size": agent.chunk_size}},
    )

    summaries: list[str] = []
    keyword_str = ", ".join(keywords)
    for chunk in chunks:
        prompt = (
            f"{prompt_prefix}Given the task: {task_goal}, "
            f"focus on the following keywords: {keyword_str}. "
            "Summarize the following text in a concise and coherent manner:"
            f"\n\n{chunk}"
        )
        try:
            summary = await agent.llm.generate(prompt, max_tokens=agent.max_tokens)
            summaries.append(summary.strip())
        except Exception as e:
            agent.logger.warning(
                f"Failed to summarize chunk: {e!s}",
                extra={"context": {"chunk": chunk[:100]}},
            )
            agent.logger_manager.log_metric(
                "abstractive_summary_errors",
                1,
                MetricType.COUNTER,
                tags={"stage": "abstractive_summary"},
            )
            summaries.append("")

    combined = " ".join(s for s in summaries if s)
    if len(combined) > agent.max_length:
        agent.logger.debug(
            "Combined summary exceeds max_length, summarizing again",
            extra={"context": {"combined_length": len(combined)}},
        )
        return await generate_abstractive_summary(
            agent,
            [{"heading": "Summary", "content": combined, "relevance_score": 1.0}],
            prompt_prefix,
            task_goal,
            keywords,
        )
    return combined
