import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict

from app.schemas.platform import PlatformResponse


class TaskCreate(BaseModel):
    name: str
    goal: str
    platform_ids: list[uuid.UUID]
    constraints: dict | None = None


class TaskUpdate(BaseModel):
    name: str | None = None
    goal: str | None = None
    platform_ids: list[uuid.UUID] | None = None
    constraints: dict | None = None


class TaskResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    goal: str
    constraints: dict | None = None
    platforms: list[PlatformResponse] = []
    created_at: datetime
    updated_at: datetime
