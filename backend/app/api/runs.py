import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.agent_run import AgentRun, RunStatus
from app.models.agent_task import AgentTask
from app.schemas.run import RunResponse

router = APIRouter(tags=["runs"])


@router.post("/api/tasks/{task_id}/run", response_model=RunResponse, status_code=201)
async def trigger_run(
    task_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    task = await db.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    run = AgentRun(task_id=task_id, status=RunStatus.PENDING)
    db.add(run)
    await db.commit()

    # Re-query with eager loading for steps relationship
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run.id)
    )
    return result.scalar_one()


@router.get("/api/runs", response_model=list[RunResponse])
async def list_runs(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .order_by(AgentRun.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return result.scalars().all()


@router.get("/api/runs/{run_id}", response_model=RunResponse)
async def get_run(
    run_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")
    return run


@router.post("/api/runs/{run_id}/cancel", response_model=RunResponse)
async def cancel_run(
    run_id: uuid.UUID, db: AsyncSession = Depends(get_db)
):
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run_id)
    )
    run = result.scalar_one_or_none()
    if not run:
        raise HTTPException(status_code=404, detail="Run not found")

    if run.status not in (RunStatus.PENDING, RunStatus.RUNNING):
        raise HTTPException(
            status_code=409,
            detail=f"Cannot cancel run with status '{run.status.value}'",
        )

    run.status = RunStatus.CANCELLED
    # TODO: revoke Celery task if celery_task_id is set
    await db.commit()

    # Re-query to get fresh state with relationships
    result = await db.execute(
        select(AgentRun)
        .options(selectinload(AgentRun.steps))
        .where(AgentRun.id == run.id)
    )
    return result.scalar_one()
