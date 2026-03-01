"""Data analysis tool — sends data + question to GPT-4o for analysis."""

from __future__ import annotations

from langchain_core.tools import tool
from langchain_openai import ChatOpenAI

from app.config import settings


def make_analyze_tool() -> callable:
    """Create a tool that sends data and a question to GPT-4o for analysis.

    The tool uses a separate LLM call (not the agent's main LLM) so the
    analysis is focused solely on the provided data and question.
    """

    @tool
    async def analyze_data(data: str, question: str) -> str:
        """Analyze data using GPT-4o and return insights.

        Use this tool when you have scraped or collected data and need to
        analyze it — for example, checking whether metrics meet a threshold
        or summarizing trends.

        Args:
            data: The data to analyze (JSON string, table text, etc.).
            question: The specific question to answer about the data.
        """
        llm = ChatOpenAI(
            model="gpt-4o",
            api_key=settings.OPENAI_API_KEY,
            temperature=0,
        )
        prompt = (
            "You are a data analyst. Analyze the following data and answer "
            "the question concisely.\n\n"
            f"DATA:\n{data}\n\n"
            f"QUESTION: {question}"
        )
        response = await llm.ainvoke(prompt)
        return response.content

    return analyze_data
