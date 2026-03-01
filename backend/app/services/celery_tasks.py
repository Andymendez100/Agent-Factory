"""Celery task that executes an agent run end-to-end.

Flow: load task + platforms → launch browser → generate tools →
build agent → stream agent → save StepLogs → update AgentRun.
"""

from __future__ import annotations

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.orm import selectinload

from app.db.session import async_session
from app.models.agent_run import AgentRun, RunStatus
from app.models.agent_task import AgentTask
from app.models.step_log import StepLog
from app.services.celery_app import celery_app
from app.services.redis_pubsub import publish_step, publish_run_complete

logger = logging.getLogger(__name__)


def _import_engine():
    """Deferred import of engine components (heavy deps: langchain, langgraph).

    Returns (BrowserPool, generate_tools, build_system_prompt, build_agent, HumanMessage).
    """
    from app.services.browser_pool import BrowserPool
    from app.engine.tool_generator import generate_tools
    from app.engine.prompts import build_system_prompt
    from app.engine.agent import build_agent
    from langchain_core.messages import HumanMessage

    return BrowserPool, generate_tools, build_system_prompt, build_agent, HumanMessage


@celery_app.task(bind=True, name="run_agent_task")
def run_agent_task(self, run_id: str):
    """Execute an agent run via the LangGraph ReAct engine."""
    logger.info("Starting agent run %s", run_id)
    asyncio.run(_execute_run(run_id))
    logger.info("Completed agent run %s", run_id)


async def _execute_run(run_id: str):
    """Async implementation of the full agent execution pipeline.

    1. Load AgentRun → AgentTask → Platforms from DB
    2. Transition status to RUNNING
    3. Launch Playwright browser, create page
    4. Generate tools from platform configs
    5. Build system prompt and LangGraph agent
    6. Stream agent events, saving each step as a StepLog
    7. Save final answer and mark COMPLETED
    8. On error: mark FAILED with error message
    """
    async with async_session() as session:
        run = await session.get(AgentRun, uuid.UUID(run_id))
        if not run:
            logger.error("Run %s not found", run_id)
            return

        try:
            # Mark as running
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Load the task with its platforms
            stmt = (
                select(AgentTask)
                .where(AgentTask.id == run.task_id)
                .options(selectinload(AgentTask.platforms))
            )
            result = await session.execute(stmt)
            task = result.scalar_one()

            # Import engine components (deferred to avoid import-time dep issues)
            (
                BrowserPool, generate_tools, build_system_prompt,
                build_agent, HumanMessage,
            ) = _import_engine()

            # Launch browser
            async with BrowserPool() as pool:
                context = await pool.new_context(
                    viewport={"width": 1280, "height": 720}
                )
                page = await context.new_page()

                try:
                    tools = generate_tools(task.platforms, page)
                    system_prompt = build_system_prompt(task, task.platforms)
                    agent = build_agent(tools, system_prompt)

                    initial_state = {
                        "messages": [HumanMessage(content=task.goal)],
                        "run_id": run_id,
                        "platform_configs": [],
                    }

                    step_index = 0
                    final_answer = None

                    async for event in agent.astream(
                        initial_state, stream_mode="updates"
                    ):
                        for node_name, node_output in event.items():
                            step_start = time.time()
                            messages = node_output.get("messages", [])

                            for msg in messages:
                                step_log = _create_step_log(
                                    run_id=run.id,
                                    step_index=step_index,
                                    node_name=node_name,
                                    message=msg,
                                )
                                session.add(step_log)
                                step_index += 1

                                # Publish step to Redis for live WS streaming
                                await publish_step(run_id, {
                                    "step_index": step_log.step_index,
                                    "step_type": step_log.step_type,
                                    "tool_name": step_log.tool_name,
                                    "tool_input": step_log.tool_input,
                                    "tool_output": step_log.tool_output,
                                    "agent_reasoning": step_log.agent_reasoning,
                                    "screenshot_path": step_log.screenshot_path,
                                    "duration_ms": step_log.duration_ms,
                                })

                                # Track final answer (last agent message without tool calls)
                                if (
                                    node_name == "agent"
                                    and hasattr(msg, "content")
                                    and msg.content
                                    and not (
                                        hasattr(msg, "tool_calls")
                                        and msg.tool_calls
                                    )
                                ):
                                    final_answer = msg.content

                            await session.commit()

                    # Mark completed
                    run.status = RunStatus.COMPLETED
                    run.finished_at = datetime.now(timezone.utc)
                    run.final_answer = final_answer or "Agent completed without a final answer."
                    await session.commit()

                    await publish_run_complete(
                        run_id, "completed", final_answer=run.final_answer
                    )

                finally:
                    await context.close()

        except Exception as e:
            logger.exception("Run %s failed: %s", run_id, e)
            await session.rollback()
            run.status = RunStatus.FAILED
            run.error = str(e)
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()

            await publish_run_complete(run_id, "failed", error=str(e))


def _create_step_log(
    run_id: uuid.UUID,
    step_index: int,
    node_name: str,
    message,
) -> StepLog:
    """Create a StepLog entry from a LangGraph stream event message."""
    step_type = "agent_thinking" if node_name == "agent" else "tool_call"

    tool_name = None
    tool_input = None
    tool_output = None
    agent_reasoning = None
    screenshot_path = None

    if step_type == "agent_thinking":
        agent_reasoning = getattr(message, "content", None)
        # If the agent is making tool calls, log them
        if hasattr(message, "tool_calls") and message.tool_calls:
            tool_calls = message.tool_calls
            tool_name = tool_calls[0].get("name") if tool_calls else None
            tool_input = tool_calls[0].get("args") if tool_calls else None
    else:
        # Tool result message
        tool_name = getattr(message, "name", None)
        content = getattr(message, "content", "")
        tool_output = {"result": content} if isinstance(content, str) else content

        # Detect screenshot paths in tool output
        if isinstance(content, str) and "screenshot" in content.lower():
            # Extract path if present (format: "Screenshot saved to /path/to/file.png")
            if "/tmp/" in content:
                screenshot_path = content.split("/tmp/", 1)[-1]
                screenshot_path = "/tmp/" + screenshot_path.split('"')[0].strip()

    return StepLog(
        run_id=run_id,
        step_index=step_index,
        step_type=step_type,
        tool_name=tool_name,
        tool_input=tool_input,
        tool_output=tool_output,
        agent_reasoning=agent_reasoning,
        screenshot_path=screenshot_path,
        duration_ms=0,
    )
