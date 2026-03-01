from sqlalchemy import LargeBinary, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin


class Platform(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "platforms"

    name: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    base_url: Mapped[str] = mapped_column(Text, nullable=False)
    login_url: Mapped[str] = mapped_column(Text, nullable=False)
    credentials_encrypted: Mapped[bytes] = mapped_column(
        LargeBinary, nullable=False
    )
    login_selectors: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    extra_config: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    tasks: Mapped[list["AgentTask"]] = relationship(
        "AgentTask",
        secondary="task_platforms",
        back_populates="platforms",
    )
