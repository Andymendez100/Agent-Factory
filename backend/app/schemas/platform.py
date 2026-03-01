import uuid
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class PlatformCreate(BaseModel):
    name: str
    base_url: str
    login_url: str
    credentials: dict[str, str]
    login_selectors: dict[str, str] = {}
    extra_config: dict | None = None


class PlatformUpdate(BaseModel):
    name: str | None = None
    base_url: str | None = None
    login_url: str | None = None
    credentials: dict[str, str] | None = None
    login_selectors: dict[str, str] | None = None
    extra_config: dict | None = None


class PlatformResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    name: str
    base_url: str
    login_url: str
    login_selectors: dict[str, str]
    extra_config: dict | None = None
    created_at: datetime
    updated_at: datetime
    # credentials_encrypted is intentionally excluded — never expose to frontend
