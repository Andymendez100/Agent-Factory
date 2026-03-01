import asyncio
import logging
import uuid
from datetime import datetime, timezone

from app.db.session import async_session
from app.models.agent_run import AgentRun, RunStatus
from app.services.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(bind=True, name="run_agent_task")
def run_agent_task(self, run_id: str):
    """Execute an agent run. Currently a placeholder that marks the run complete."""
    logger.info("Starting agent run %s", run_id)
    asyncio.run(_execute_run(run_id))
    logger.info("Completed agent run %s", run_id)


async def _execute_run(run_id: str):
    """Async implementation of the agent run execution.

    Placeholder: sets status to RUNNING, sleeps 5s, then marks COMPLETED.
    Will be replaced with the real LangGraph agent engine in Task 16.
    """
    async with async_session() as session:
        run = await session.get(AgentRun, uuid.UUID(run_id))
        if not run:
            logger.error("Run %s not found", run_id)
            return

        try:
            run.status = RunStatus.RUNNING
            run.started_at = datetime.now(timezone.utc)
            await session.commit()

            # Placeholder: simulate work
            await asyncio.sleep(5)

            run.status = RunStatus.COMPLETED
            run.finished_at = datetime.now(timezone.utc)
            run.final_answer = "Placeholder: agent task completed successfully."
            await session.commit()

        except Exception as e:
            logger.exception("Run %s failed: %s", run_id, e)
            await session.rollback()
            run.status = RunStatus.FAILED
            run.error = str(e)
            run.finished_at = datetime.now(timezone.utc)
            await session.commit()
