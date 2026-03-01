"""System prompt builder for the ReAct agent."""

from __future__ import annotations

import json
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from app.models.agent_task import AgentTask
    from app.models.platform import Platform

SYSTEM_PROMPT_TEMPLATE = """\
You are an AI agent for BPO operations. You have access to browser automation tools \
and data analysis capabilities.

Your goal: {goal}

Available platforms: {platform_names}

{constraints_section}\
Instructions:
- Use the login tools to access platforms as needed
- Navigate to relevant pages and scrape data
- Analyze data against the provided constraints
- Report your findings clearly
- Take screenshots of important data for evidence"""


def build_system_prompt(
    task: AgentTask,
    platforms: list[Platform],
) -> str:
    """Build the system prompt for a given task and its platforms.

    Formats the goal, platform names, and constraints into a prompt
    that tells the LLM what to accomplish and what tools are available.
    """
    platform_names = ", ".join(p.name for p in platforms) if platforms else "none"

    constraints_section = ""
    if task.constraints:
        formatted = json.dumps(task.constraints, indent=2)
        constraints_section = f"Constraints: {formatted}\n\n"

    return SYSTEM_PROMPT_TEMPLATE.format(
        goal=task.goal,
        platform_names=platform_names,
        constraints_section=constraints_section,
    )
