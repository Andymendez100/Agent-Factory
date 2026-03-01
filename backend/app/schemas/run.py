import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.step_log import StepLogResponse


class RunResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    task_id: uuid.UUID
    status: str
    started_at: datetime | None = None
    finished_at: datetime | None = None
    final_answer: str | None = None
    error: str | None = None
    celery_task_id: str | None = None
    steps: list[StepLogResponse] = []
    created_at: datetime
