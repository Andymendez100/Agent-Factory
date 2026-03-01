import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StepLogResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    run_id: uuid.UUID
    step_index: int
    step_type: str
    tool_name: str | None = None
    tool_input: dict | None = None
    tool_output: dict | None = None
    agent_reasoning: str | None = None
    screenshot_path: str | None = None
    duration_ms: int
    created_at: datetime
