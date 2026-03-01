import uuid

from sqlalchemy import Column, ForeignKey, String, Table, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, TimestampMixin, UUIDMixin

# Many-to-many association table for AgentTask <-> Platform
task_platforms = Table(
    "task_platforms",
    Base.metadata,
    Column("task_id", UUID(as_uuid=True), ForeignKey("agent_tasks.id", ondelete="CASCADE"), primary_key=True),
    Column("platform_id", UUID(as_uuid=True), ForeignKey("platforms.id", ondelete="CASCADE"), primary_key=True),
)


class AgentTask(Base, UUIDMixin, TimestampMixin):
    __tablename__ = "agent_tasks"

    name: Mapped[str] = mapped_column(String(255), nullable=False)
    goal: Mapped[str] = mapped_column(Text, nullable=False)
    constraints: Mapped[dict | None] = mapped_column(JSONB, nullable=True)

    platforms: Mapped[list["Platform"]] = relationship(
        "Platform",
        secondary=task_platforms,
        back_populates="tasks",
        lazy="selectin",
    )
    runs: Mapped[list["AgentRun"]] = relationship(
        "AgentRun", back_populates="task", cascade="all, delete-orphan"
    )
