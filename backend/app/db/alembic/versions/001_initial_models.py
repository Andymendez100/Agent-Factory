"""Initial models: Platform, AgentTask, AgentRun, StepLog

Revision ID: 001
Revises:
Create Date: 2026-02-28

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Run status enum
    run_status = postgresql.ENUM(
        "pending", "running", "completed", "failed", "cancelled",
        name="run_status", create_type=True,
    )
    run_status.create(op.get_bind(), checkfirst=True)

    # Platforms table
    op.create_table(
        "platforms",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), unique=True, nullable=False),
        sa.Column("base_url", sa.Text, nullable=False),
        sa.Column("login_url", sa.Text, nullable=False),
        sa.Column("credentials_encrypted", sa.LargeBinary, nullable=False),
        sa.Column("login_selectors", postgresql.JSONB, nullable=False, server_default="{}"),
        sa.Column("extra_config", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Agent tasks table
    op.create_table(
        "agent_tasks",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("goal", sa.Text, nullable=False),
        sa.Column("constraints", postgresql.JSONB, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    # Many-to-many: task <-> platform
    op.create_table(
        "task_platforms",
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("platform_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("platforms.id", ondelete="CASCADE"), primary_key=True),
    )

    # Agent runs table
    op.create_table(
        "agent_runs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("task_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_tasks.id", ondelete="CASCADE"), nullable=False),
        sa.Column("status", run_status, nullable=False, server_default="pending"),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("final_answer", sa.Text, nullable=True),
        sa.Column("error", sa.Text, nullable=True),
        sa.Column("celery_task_id", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_agent_runs_task_id", "agent_runs", ["task_id"])

    # Step logs table
    op.create_table(
        "step_logs",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column("run_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("agent_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("step_index", sa.Integer, nullable=False),
        sa.Column("step_type", sa.String(50), nullable=False),
        sa.Column("tool_name", sa.String(255), nullable=True),
        sa.Column("tool_input", postgresql.JSONB, nullable=True),
        sa.Column("tool_output", postgresql.JSONB, nullable=True),
        sa.Column("agent_reasoning", sa.Text, nullable=True),
        sa.Column("screenshot_path", sa.String(512), nullable=True),
        sa.Column("duration_ms", sa.Integer, nullable=False, server_default="0"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_step_logs_run_id", "step_logs", ["run_id"])


def downgrade() -> None:
    op.drop_table("step_logs")
    op.drop_table("agent_runs")
    op.drop_table("task_platforms")
    op.drop_table("agent_tasks")
    op.drop_table("platforms")
    op.execute("DROP TYPE IF EXISTS run_status")
