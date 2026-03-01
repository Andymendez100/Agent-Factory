import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.session import get_db
from app.models.agent_task import AgentTask
from app.models.platform import Platform
from app.schemas.task import TaskCreate, TaskResponse, TaskUpdate

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


async def _resolve_platforms(
    platform_ids: list[uuid.UUID], db: AsyncSession
) -> list[Platform]:
    """Fetch platforms by IDs, raise 400 if any are missing."""
    result = await db.execute(
        select(Platform).where(Platform.id.in_(platform_ids))
    )
    platforms = result.scalars().all()
    found_ids = {p.id for p in platforms}
    missing = set(platform_ids) - found_ids
    if missing:
        raise HTTPException(
            status_code=400,
            detail=f"Platform(s) not found: {[str(m) for m in missing]}",
        )
    return list(platforms)


@router.post("", response_model=TaskResponse, status_code=201)
async def create_task(body: TaskCreate, db: AsyncSession = Depends(get_db)):
    platforms = await _resolve_platforms(body.platform_ids, db)
    task = AgentTask(
        name=body.name,
        goal=body.goal,
        constraints=body.constraints,
    )
    task.platforms = platforms
    db.add(task)
    await db.commit()
    await db.refresh(task)
    return task


@router.get("", response_model=list[TaskResponse])
async def list_tasks(db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTask)
        .options(selectinload(AgentTask.platforms))
        .order_by(AgentTask.created_at.desc())
    )
    return result.scalars().all()


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(AgentTask)
        .options(selectinload(AgentTask.platforms))
        .where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return task


@router.put("/{task_id}", response_model=TaskResponse)
async def update_task(
    task_id: uuid.UUID,
    body: TaskUpdate,
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(AgentTask)
        .options(selectinload(AgentTask.platforms))
        .where(AgentTask.id == task_id)
    )
    task = result.scalar_one_or_none()
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    update_data = body.model_dump(exclude_unset=True)

    if "platform_ids" in update_data:
        platforms = await _resolve_platforms(update_data.pop("platform_ids"), db)
        task.platforms = platforms

    for field, value in update_data.items():
        setattr(task, field, value)

    await db.commit()
    await db.refresh(task)
    return task


@router.delete("/{task_id}", status_code=204)
async def delete_task(task_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    task = await db.get(AgentTask, task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    await db.delete(task)
    await db.commit()
